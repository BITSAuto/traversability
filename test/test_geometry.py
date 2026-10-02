import numpy as np
import pytest

from traversability import geometry
from traversability.geometry import DROP, GROUND, OBSTACLE, OVERHEAD, UNKNOWN, Plane
from traversability.grid import FREE, LETHAL, NO_INFO, GridSpec, rasterize
from traversability.transforms import matrix_to_quaternion, quaternion_to_matrix

FX = FY = 446.8
CX, CY = 424.0, 240.0
W, H = 848, 480


def render_depth(camera_height=1.24, pitch_deg=3.0, boxes=(), max_range=10.0):
    """Planar depth of a flat ground plane (plus axis-aligned boxes) seen by a
    camera pitched down by ``pitch_deg``. Boxes are (x0, x1, y0, y1, height)
    in the ground frame (X forward, Y left). Ray-cast per pixel."""
    v, u = np.mgrid[0:H, 0:W].astype(float)
    rays = np.stack(((u - CX) / FX, (v - CY) / FY, np.ones_like(u)), axis=-1)   # optical, z = 1
    p = np.radians(pitch_deg)
    # optical -> ground: x_g = z_o, y_g = -x_o, z_g = -y_o, then pitch down about y_g.
    to_ground = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], float)
    pitch = np.array([[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]])
    d = rays @ (pitch @ to_ground).T                                           # ground-frame dirs
    origin = np.array([0, 0, camera_height])

    t = np.full((H, W), np.inf)
    down = d[..., 2] < 0
    t[down] = -camera_height / d[down][:, 2]
    for x0, x1, y0, y1, h in boxes:
        lo = np.array([x0, y0, 0.0]) - origin
        hi = np.array([x1, y1, h]) - origin
        with np.errstate(divide='ignore', invalid='ignore'):
            t0, t1 = lo / d, hi / d
        tmin = np.nanmax(np.minimum(t0, t1), axis=-1)
        tmax = np.nanmin(np.maximum(t0, t1), axis=-1)
        hit = (tmax >= tmin) & (tmin > 0)
        t[hit] = np.minimum(t[hit], tmin[hit])
    depth = t.astype(np.float32)          # ray parameter == planar depth (z = 1)
    depth[depth > max_range] = np.inf
    return depth


def pitched_up(pitch_deg):
    # Ground "up" in the optical frame of a camera pitched down by pitch_deg:
    # the optical axis tilts towards the ground, away from up.
    p = np.radians(pitch_deg)
    return np.array([0.0, -np.cos(p), -np.sin(p)])


def fit(depth, up):
    points = geometry.deproject(depth, FX, FY, CX, CY, step=2, max_range=10.0)
    valid = points[np.isfinite(points[..., 2])]
    return points, geometry.fit_ground_plane(valid, up, np.random.default_rng(0))


def test_fit_recovers_height_and_tilt():
    depth = render_depth(camera_height=1.24, pitch_deg=3.0, boxes=[(5, 6, -1, 1, 1.0)])
    _, plane = fit(depth, np.array([0.0, -1.0, 0.0]))     # level prior, 3 deg off
    assert plane is not None
    assert plane.offset == pytest.approx(1.24, abs=0.01)
    assert np.degrees(np.arccos(np.clip(plane.normal @ pitched_up(3.0), -1, 1))) < 0.5


def test_fit_rejects_planes_outside_constraints():
    depth = render_depth(camera_height=1.24)
    points = geometry.deproject(depth, FX, FY, CX, CY, step=2)
    valid = points[np.isfinite(points[..., 2])]
    rng = np.random.default_rng(0)
    # Prior 45 deg off: the true ground is outside the tilt tolerance.
    tilted = np.array([0.0, -np.cos(np.radians(45)), np.sin(np.radians(45))])
    assert geometry.fit_ground_plane(valid, tilted, rng, max_tilt_deg=20) is None
    # Camera height outside the allowed range.
    assert geometry.fit_ground_plane(valid, pitched_up(0), rng, height_range=(2.0, 3.0)) is None


def test_flat_patch_is_ground_and_box_is_obstacle():
    boxes = [(4.0, 4.5, -0.5, 0.5, 0.004),    # newspaper-thin patch
             (6.0, 6.5, -2.0, -1.5, 0.15),    # curb-height brick
             (7.0, 7.5, 1.0, 1.5, 0.5)]       # box
    depth = render_depth(boxes=boxes)
    points, plane = fit(depth, pitched_up(3.0))
    rotation, origin = geometry.ground_frame(plane)
    ground = geometry.to_ground(points, rotation, origin)
    labels = geometry.classify(ground, points[..., 2], plane.offset, obstacle_height=0.08)

    x, y = ground[..., 0], ground[..., 1]

    def labels_in(x0, x1, y0, y1):
        m = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        return labels[m]

    assert np.all(labels_in(4.05, 4.45, -0.45, 0.45) == GROUND)
    assert np.any(labels_in(5.95, 6.55, -2.05, -1.45) == OBSTACLE)
    assert np.any(labels_in(6.95, 7.55, 0.95, 1.55) == OBSTACLE)
    # Away from the objects the road is all ground.
    assert np.all(labels_in(3.0, 3.9, -3.0, 3.0) == GROUND)


def test_ground_frame_axes():
    plane = Plane(pitched_up(5.0), 1.3)
    rotation, origin = geometry.ground_frame(plane)
    np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
    assert np.linalg.det(rotation) == pytest.approx(1.0)
    # Camera sits 1.3 m straight above the ground-frame origin.
    np.testing.assert_allclose(geometry.to_ground(np.zeros(3), rotation, origin), [0, 0, 1.3], atol=1e-9)
    # Optical +Z (forward) maps to ground +X, optical +X (right) to ground -Y.
    assert geometry.to_ground(np.array([0, 0, 1.0]), rotation, np.zeros(3))[0] > 0.99
    assert geometry.to_ground(np.array([1.0, 0, 0]), rotation, np.zeros(3))[1] == pytest.approx(-1.0)


def test_classify_thresholds_and_noise_scaling():
    pts = np.array([[5, 0, 0.0], [5, 0, 0.09], [5, 0, 0.3], [5, 0, 3.0], [5, 0, -0.3], [5, 0, np.nan]])
    depth = np.full(len(pts), 5.0)
    labels = geometry.classify(pts, depth, 1.24, obstacle_height=0.08)
    assert list(labels) == [GROUND, OBSTACLE, OBSTACLE, OVERHEAD, DROP, UNKNOWN]
    # With depth noise the tolerance at 5 m grows past 9 cm.
    noisy = geometry.classify(pts, depth, 1.24, obstacle_height=0.08, depth_noise_coeff=0.005, noise_sigmas=2)
    assert noisy[1] == GROUND


def test_tracker_smooths_and_rejects_jumps():
    tracker = geometry.GroundPlaneTracker(alpha=0.5, max_rejections=3)
    base = Plane(pitched_up(0), 1.2)
    assert tracker.update(base) is base
    assert tracker.update(Plane(pitched_up(0), 1.24)).offset == pytest.approx(1.22)
    # A 1 m jump is rejected until it persists for max_rejections frames.
    jump = Plane(pitched_up(0), 2.2)
    assert tracker.update(jump).offset == pytest.approx(1.22)
    assert tracker.update(jump).offset == pytest.approx(1.22)
    assert tracker.update(jump).offset == pytest.approx(2.2)
    # Missing fits hold the plane for a while, then drop it.
    for _ in range(tracker.max_hold_frames):
        assert tracker.update(None) is not None
    assert tracker.update(None) is None


def test_rasterize():
    spec = GridSpec(0.0, 2.0, -1.0, 1.0, 0.5)
    points = np.array([[0.2, -0.8, 0], [1.2, 0.2, 0.3], [1.3, 0.3, 0.4], [1.4, 0.1, 0.5],
                       [1.7, 0.7, 0.2], [5.0, 0.0, 0.0]])
    labels = np.array([GROUND, OBSTACLE, OBSTACLE, OBSTACLE, OBSTACLE, GROUND], np.uint8)
    grid = rasterize(points, labels, spec, min_obstacle_points=3)
    assert grid.shape == (4, 4)
    assert grid[0, 0] == FREE                 # y=-0.8 -> row 0, x=0.2 -> col 0
    assert grid[2, 2] == LETHAL               # three obstacle points
    assert grid[3, 3] == NO_INFO              # a single obstacle point is speckle
    assert np.count_nonzero(grid != NO_INFO) == 2


def test_quaternion_roundtrip():
    rng = np.random.default_rng(3)
    for _ in range(20):
        q = rng.normal(size=4)
        q /= np.linalg.norm(q)
        m = quaternion_to_matrix(*q)
        q2 = np.array(matrix_to_quaternion(m))
        assert min(np.abs(q - q2).max(), np.abs(q + q2).max()) < 1e-9


def test_fill_ground_gaps():
    from traversability.grid import fill_ground_gaps
    # One image column: two ground pixels 0.5 m apart, then ground -> obstacle.
    points = np.array([[[2.0, 0, 0]], [[2.5, 0, 0]], [[3.0, 0, 0.3]], [[5.0, 0, 0]]])
    labels = np.array([[GROUND], [GROUND], [OBSTACLE], [GROUND]], np.uint8)
    filled = fill_ground_gaps(points, labels, resolution=0.1, max_gap=1.0)
    assert len(filled) > 0
    assert filled[:, 0].min() > 2.0 and filled[:, 0].max() < 2.5     # only between the ground pair
    spec = GridSpec(0.0, 6.0, -0.5, 0.5, 0.1)
    grid = rasterize(np.concatenate((points.reshape(-1, 3), filled)),
                     np.concatenate((labels.ravel(), np.full(len(filled), GROUND, np.uint8))), spec)
    row = spec.cell(0.0, 0.0)[0]
    assert np.all(grid[row, 20:26] == FREE)
    assert fill_ground_gaps(points, labels, 0.1, max_gap=0.0).shape == (0, 3)
