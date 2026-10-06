import numpy as np

from traversability import fusion, semantics
from traversability.fusion import FusionParams
from traversability.geometry import GROUND, OBSTACLE
from traversability.grid import FREE, LETHAL, NO_INFO, GridSpec, fill_ground_gaps
from traversability.semantics import NONE, OTHER, ROAD, SIDEWALK, TERRAIN

SPEC = GridSpec(0.0, 10.0, -5.0, 5.0, 0.1)


def dense_scene(regions, obstacles=()):
    """One ground point per 5 cm over the grid; ``regions`` paints semantic
    classes as (x0, x1, y0, y1, cls) boxes over a ROAD background."""
    xs, ys = np.meshgrid(np.arange(0.025, 10, 0.05), np.arange(-4.975, 5, 0.05))
    points = np.stack((xs, ys, np.zeros_like(xs)), axis=-1)
    labels = np.full(xs.shape, GROUND, np.uint8)
    classes = np.full(xs.shape, ROAD, np.uint8)
    for x0, x1, y0, y1, cls in regions:
        classes[(xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)] = cls
    for x0, x1, y0, y1 in obstacles:
        labels[(xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)] = OBSTACLE
    return points, labels, classes


def cell(grid, x, y):
    row, col = SPEC.cell(x, y)
    return grid[row, col]


def test_small_other_patch_on_road_is_free():
    points, labels, classes = dense_scene([(4.0, 4.6, -0.3, 0.3, OTHER)])       # newspaper
    grid, _ = fusion.fuse(points, labels, classes, SPEC)
    assert cell(grid, 4.3, 0.0) == FREE
    assert np.all(grid == FREE)


def test_large_other_region_stays_lethal():
    points, labels, classes = dense_scene([(3.0, 6.0, -2.0, 2.0, OTHER)])       # 12 m^2
    grid, _ = fusion.fuse(points, labels, classes, SPEC)
    assert cell(grid, 4.5, 0.0) == LETHAL


def test_other_patch_not_surrounded_by_road_stays_lethal():
    # A small unknown patch on a grass verge.
    points, labels, classes = dense_scene([(2.0, 8.0, 1.0, 5.0, TERRAIN), (4.0, 4.6, 2.0, 2.6, OTHER)])
    grid, _ = fusion.fuse(points, labels, classes, SPEC)
    assert cell(grid, 4.3, 2.3) == LETHAL


def test_forbidden_surfaces_are_lethal_and_obstacles_win():
    points, labels, classes = dense_scene([(2.0, 8.0, 3.0, 5.0, SIDEWALK), (2.0, 8.0, -5.0, -3.0, TERRAIN)],
                                          obstacles=[(6.0, 6.5, -0.25, 0.25)])
    grid, cells = fusion.fuse(points, labels, classes, SPEC)
    assert cell(grid, 5.0, 4.0) == LETHAL
    assert cell(grid, 5.0, -4.0) == LETHAL
    assert cell(grid, 6.2, 0.0) == LETHAL and cell(cells, 6.2, 0.0) == fusion.CELL_OBSTACLE
    assert cell(grid, 5.0, 0.0) == FREE


def test_patch_next_to_obstacle_still_free():
    points, labels, classes = dense_scene([(4.0, 4.6, -0.3, 0.3, OTHER)], obstacles=[(4.6, 5.0, -0.3, 0.3)])
    grid, _ = fusion.fuse(points, labels, classes, SPEC)
    assert cell(grid, 4.3, 0.0) == FREE


def test_ground_without_semantics():
    points, labels, classes = dense_scene([(0.0, 10.0, -5.0, 5.0, NONE)])
    grid, _ = fusion.fuse(points, labels, classes, SPEC)
    assert np.all(grid == NO_INFO)
    grid, _ = fusion.fuse(points, labels, classes, SPEC, FusionParams(unlabelled_ground='free'))
    assert np.all(grid == FREE)


def test_tie_goes_to_forbidden():
    points = np.array([[1.05, 0.05, 0.0], [1.06, 0.06, 0.0]])
    labels = np.array([GROUND, GROUND], np.uint8)
    classes = np.array([ROAD, SIDEWALK], np.uint8)
    cells = fusion.cell_classes(points, labels, classes, SPEC)
    assert cell(cells, 1.05, 0.05) == fusion.CELL_FORBIDDEN


def test_sample_semantics_projection():
    # Camera 1 m above the ground origin looking along +X (optical Z).
    # Ground (x fwd, y left, z up) -> optical (x right, y down, z fwd).
    rotation = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)
    translation = np.array([0.0, 1.0, 0.0])
    classes = np.zeros((480, 640), np.uint8)
    classes[300:, :320] = TERRAIN     # lower-left quadrant
    classes[300:, 320:] = ROAD        # lower-right quadrant
    points = np.array([[[5.0, 1.0, 0.0], [5.0, -1.0, 0.0], [-5.0, 0.0, 0.0]]])   # left, right, behind
    out = fusion.sample_semantics(points, rotation, translation, 500, 500, 320, 240, classes)
    assert list(out[0]) == [TERRAIN, ROAD, NONE]


def test_fill_ground_gaps_keeps_classes():
    points = np.array([[[2.0, 0, 0]], [[2.5, 0, 0]], [[3.0, 0, 0]]])
    labels = np.full((3, 1), GROUND, np.uint8)
    classes = np.array([[ROAD], [ROAD], [TERRAIN]], np.uint8)
    filled, filled_classes = fill_ground_gaps(points, labels, 0.1, 1.0, classes)
    assert len(filled) > 0 and np.all(filled[:, 0] < 2.5)      # only the road-road pair
    assert np.all(filled_classes == ROAD)


def test_label_mappings():
    city = ['road', 'sidewalk', 'building', 'vegetation', 'terrain', 'sky', 'car']
    assert list(semantics.class_lut(city)) == [ROAD, SIDEWALK, OTHER, TERRAIN, TERRAIN, OTHER, OTHER]
    mapillary = ['Lane Marking - General', 'Manhole', 'Curb', 'Pothole', 'Ego Vehicle']
    assert list(semantics.class_lut(mapillary)) == [ROAD, ROAD, SIDEWALK, OTHER, semantics.IGNORE]
    m = semantics.aggregation_matrix(mapillary)
    assert m.shape == (semantics.NUM_CLASSES, 5)
    assert m[:, 4].sum() == 0 and m[ROAD - 1, :2].sum() == 2
