"""Bird's-eye occupancy grid from labelled ground-frame points (pure numpy)."""

from dataclasses import dataclass

import numpy as np

from traversability.geometry import DROP, GROUND, OBSTACLE

# nav_msgs/OccupancyGrid cell values.
FREE = 0
LETHAL = 100
NO_INFO = -1


@dataclass(frozen=True)
class GridSpec:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    resolution: float

    @property
    def width(self):   # cells along X (columns)
        return int(round((self.x_max - self.x_min) / self.resolution))

    @property
    def height(self):  # cells along Y (rows)
        return int(round((self.y_max - self.y_min) / self.resolution))

    def cell(self, x, y):
        """(row, col) index arrays for ground-frame coordinates."""
        col = np.floor((np.asarray(x) - self.x_min) / self.resolution).astype(np.int64)
        row = np.floor((np.asarray(y) - self.y_min) / self.resolution).astype(np.int64)
        return row, col


def fill_ground_gaps(points, labels, resolution, max_gap=1.0, classes=None):
    """Interpolate ground points between vertically adjacent ground pixels.

    Far from the camera, consecutive image rows hit the road further apart
    than a grid cell, leaving stripes of unseen cells across clearly visible
    road. If two vertically adjacent pixels are both ground, nothing in the
    image lies between them, so the road between them is visible too --
    unless the gap is large enough to hide a hole, hence ``max_gap``.

    Takes the organised (H, W, 3) points and (H, W) labels; returns extra
    (N, 3) points, all ground. With per-point semantic ``classes`` (H, W),
    only pairs of the same class are filled, and the filled points' classes
    are returned too: ``(points, classes)``.
    """
    empty = np.empty((0, 3), dtype=points.dtype)
    if max_gap <= 0:
        return empty if classes is None else (empty, np.empty(0, np.uint8))
    a, b = points[:-1], points[1:]
    pair = (labels[:-1] == GROUND) & (labels[1:] == GROUND)
    if classes is not None:
        pair &= classes[:-1] == classes[1:]
    gap = np.linalg.norm((b - a)[..., :2], axis=-1)
    pair &= (gap > resolution) & (gap <= max_gap)
    a, b = a[pair], b[pair]
    # Enough samples that even a max_gap segment gets one per cell.
    steps = int(np.ceil(max_gap / resolution))
    t = (np.arange(1, steps) / steps)[None, :, None]                    # (1, S, 1)
    filled = (a[:, None] + t * (b - a)[:, None]).reshape(-1, 3)
    if classes is None:
        return filled
    return filled, np.repeat(classes[:-1][pair], steps - 1)


def rasterize(points, labels, spec, *, min_obstacle_points=3, min_ground_points=1):
    """Build an occupancy grid (rows = Y, cols = X, int8) from points.

    A cell is LETHAL if it holds at least ``min_obstacle_points`` obstacle or
    drop points, FREE if it holds at least ``min_ground_points`` ground points
    and is not lethal, and NO_INFO otherwise (never seen, or only seen as
    overhead or masked points). Requiring several obstacle points per cell
    suppresses isolated depth speckle without hiding real obstacles, whose
    vertical faces stack many points into the same cell.
    """
    points = points.reshape(-1, points.shape[-1])
    labels = labels.reshape(-1)
    finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
    points, labels = points[finite], labels[finite]
    row, col = spec.cell(points[:, 0], points[:, 1])
    inside = (row >= 0) & (row < spec.height) & (col >= 0) & (col < spec.width)
    flat = row[inside] * spec.width + col[inside]
    labels = labels[inside]
    size = spec.width * spec.height

    obstacles = np.bincount(flat[(labels == OBSTACLE) | (labels == DROP)], minlength=size)
    ground = np.bincount(flat[labels == GROUND], minlength=size)

    grid = np.full(size, NO_INFO, dtype=np.int8)
    grid[ground >= min_ground_points] = FREE
    grid[obstacles >= min_obstacle_points] = LETHAL
    return grid.reshape(spec.height, spec.width)
