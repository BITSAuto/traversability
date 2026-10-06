"""Geometry + semantics fusion into a traversability grid (pure numpy + cv2).

Per point, geometry says ground / obstacle / drop and the semantic model says
road / sidewalk / terrain / other. Per cell:

  obstacle or drop                          -> LETHAL (geometry always wins)
  ground, mostly road                       -> FREE
  ground, mostly sidewalk or terrain        -> LETHAL (forbidden surface)
  ground, mostly "other"                    -> a patch candidate, see below
  ground, no semantics (outside the image)  -> NO_INFO by default

Patch candidates are grouped into connected components. A component that is
small and surrounded by road is something lying on the road -- paint, a
newspaper, an oil stain, a manhole -- and becomes FREE; anything else stays
LETHAL. This is the rule that fixes the original YOLO failure: the model may
well call a newspaper "not road", but geometry says it is flat and the
surroundings say it is on the road.
"""

from dataclasses import dataclass

import cv2
import numpy as np

from traversability.geometry import DROP, GROUND, OBSTACLE
from traversability.grid import FREE, LETHAL, NO_INFO
from traversability.semantics import NONE, OTHER, ROAD, SIDEWALK, TERRAIN

# Per-cell decided class, before the patch rule (also handy for debugging).
CELL_UNSEEN, CELL_OBSTACLE, CELL_ROAD, CELL_FORBIDDEN, CELL_OTHER, CELL_NOSEM = range(6)


@dataclass(frozen=True)
class FusionParams:
    min_obstacle_points: int = 3
    max_patch_area: float = 2.0         # m^2; larger "other" regions stay lethal
    enclosure_fraction: float = 0.75    # share of a patch's border that must be road
    enclosure_margin: int = 2           # border ring width, cells
    unlabelled_ground: str = 'unknown'  # 'unknown' (-1) or 'free' for ground with no semantics


def sample_semantics(points, rotation, translation, fx, fy, cx, cy, classes):
    """Semantic class for each (..., 3) ground-frame point.

    ``rotation``/``translation`` map ground-frame points into the colour
    camera's optical frame (p_cam = R p + t); ``classes`` is the colour-image
    class map. Points that don't project into the image get NONE.
    """
    p = points @ np.asarray(rotation).T + translation
    out = np.full(points.shape[:-1], NONE, np.uint8)
    z = p[..., 2]
    ok = np.isfinite(z) & (z > 1e-3)
    u = np.full(z.shape, -1, np.int64)
    v = np.full(z.shape, -1, np.int64)
    u[ok] = np.floor(fx * p[..., 0][ok] / z[ok] + cx).astype(np.int64)
    v[ok] = np.floor(fy * p[..., 1][ok] / z[ok] + cy).astype(np.int64)
    h, w = classes.shape
    ok &= (u >= 0) & (u < w) & (v >= 0) & (v < h)
    out[ok] = classes[v[ok], u[ok]]
    return out


def cell_classes(points, labels, semantics, spec, min_obstacle_points=3):
    """(rows=Y, cols=X) map of CELL_* values from labelled, classified points."""
    points = points.reshape(-1, 3)
    labels = labels.reshape(-1)
    semantics = semantics.reshape(-1)
    finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
    row, col = spec.cell(points[finite, 0], points[finite, 1])
    labels, semantics = labels[finite], semantics[finite]
    inside = (row >= 0) & (row < spec.height) & (col >= 0) & (col < spec.width)
    flat = row[inside] * spec.width + col[inside]
    labels, semantics = labels[inside], semantics[inside]
    size = spec.width * spec.height

    def count(mask):
        return np.bincount(flat[mask], minlength=size)

    ground = labels == GROUND
    obstacle = count((labels == OBSTACLE) | (labels == DROP))
    votes = np.stack([
        count(ground & (semantics == ROAD)),
        count(ground & ((semantics == SIDEWALK) | (semantics == TERRAIN))),
        count(ground & (semantics == OTHER)),
        count(ground & (semantics == NONE)),
    ])
    labelled = votes[:3].sum(axis=0)

    cells = np.full(size, CELL_UNSEEN, np.uint8)
    cells[votes[3] > 0] = CELL_NOSEM
    # Majority over labelled ground votes; argmax takes the first maximum, so
    # ties go to the more cautious class: forbidden > other > road.
    order = np.array([CELL_FORBIDDEN, CELL_OTHER, CELL_ROAD])
    winner = order[np.argmax(votes[[1, 2, 0]], axis=0)]
    cells[labelled > 0] = winner[labelled > 0]
    cells[obstacle >= min_obstacle_points] = CELL_OBSTACLE
    return cells.reshape(spec.height, spec.width)


def resolve(cells, resolution, params=FusionParams()):
    """Turn CELL_* classes into an occupancy grid, applying the patch rule."""
    grid = np.full(cells.shape, NO_INFO, np.int8)
    grid[(cells == CELL_ROAD)] = FREE
    grid[(cells == CELL_OBSTACLE) | (cells == CELL_FORBIDDEN)] = LETHAL
    if params.unlabelled_ground == 'free':
        grid[cells == CELL_NOSEM] = FREE

    other = (cells == CELL_OTHER).astype(np.uint8)
    if not other.any():
        return grid
    count, components, stats, _ = cv2.connectedComponentsWithStats(other, connectivity=8)
    kernel = np.ones((3, 3), np.uint8)
    max_cells = params.max_patch_area / (resolution * resolution)
    for i in range(1, count):
        component = components == i
        grid[component] = LETHAL
        if stats[i, cv2.CC_STAT_AREA] > max_cells:
            continue
        ring = cv2.dilate(component.astype(np.uint8), kernel, iterations=params.enclosure_margin).astype(bool)
        ring &= ~component
        ring_cells = cells[ring]
        # Obstacles next to a patch are neutral; unseen or unlabelled
        # neighbours count against it -- we can't confirm it's on the road.
        road = np.count_nonzero(ring_cells == CELL_ROAD)
        judged = np.count_nonzero(ring_cells != CELL_OBSTACLE)
        if judged and road >= params.enclosure_fraction * judged:
            grid[component] = FREE
    return grid


def fuse(points, labels, semantics, spec, params=FusionParams()):
    """Full fusion: points + geometry labels + per-point semantics -> grid."""
    cells = cell_classes(points, labels, semantics, spec, params.min_obstacle_points)
    return resolve(cells, spec.resolution, params), cells
