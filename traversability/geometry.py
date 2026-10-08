"""Ground-plane geometry for depth images.

Pure numpy, no ROS, so it can be unit-tested offline and reused unchanged on
the Jetson. Conventions:

* Camera points are in the camera-optical frame: X right, Y down, Z forward.
* The ground plane is ``n . p + d = 0`` with ``n`` a unit normal pointing up
  (towards the camera's side of the plane), so ``n . p + d`` is a point's
  signed height above the ground and ``d`` is the camera's own height.
* The ground frame sits on the plane directly below the camera: X forward
  (the camera's optical axis projected onto the plane), Y left, Z up.
"""

from dataclasses import dataclass

import numpy as np

# Per-point labels. Kept as plain ints so they survive a float32 PointCloud2
# field and numpy comparisons without conversion.
UNKNOWN = 0     # no valid depth, or masked out (e.g. the vehicle's own body)
GROUND = 1      # within tolerance of the ground plane -- paint, paper, etc.
OBSTACLE = 2    # above the ground by more than the obstacle threshold
DROP = 3        # below the ground by more than the drop threshold
OVERHEAD = 4    # above the vehicle's clearance height, so not in the way


@dataclass(frozen=True)
class Plane:
    normal: np.ndarray  # (3,) unit vector, pointing up
    offset: float       # camera height above the plane, metres

    def height(self, points):
        """Signed height above the plane of (..., 3) points."""
        return points @ self.normal + self.offset


def deproject(depth, fx, fy, cx, cy, step=1, min_range=0.0, max_range=np.inf):
    """Back-project a planar-depth image (metres) to an organised point image.

    Returns an (H', W', 3) float32 array in the optical frame, subsampled by
    ``step``; pixels with no valid depth in (min_range, max_range) are NaN.
    """
    z = np.asarray(depth, dtype=np.float32)[::step, ::step]
    valid = np.isfinite(z) & (z > min_range) & (z < max_range)
    z = np.where(valid, z, np.float32(np.nan))
    v, u = np.mgrid[0:depth.shape[0]:step, 0:depth.shape[1]:step].astype(np.float32)
    return np.stack(((u - cx) * z / fx, (v - cy) * z / fy, z), axis=-1)


def up_from_accelerometer(accel, rotation):
    """Unit "up" vector in the camera frame from an accelerometer reading.

    At rest an accelerometer measures the reaction to gravity, which points
    up. ``rotation`` maps vectors from the IMU frame into the camera frame.
    """
    up = rotation @ np.asarray(accel, dtype=float)
    norm = np.linalg.norm(up)
    return up / norm if norm > 1e-6 else None


def _orient_up(normals, offsets, up):
    flip = normals @ up < 0
    normals[flip] *= -1
    offsets[flip] *= -1
    return normals, offsets


def _refit(points, mask, up):
    """Least-squares plane through ``points[mask]`` (SVD), oriented up."""
    inliers = points[mask]
    centroid = inliers.mean(axis=0)
    normal = np.linalg.svd(inliers - centroid, full_matrices=False)[2][-1]
    if normal @ up < 0:
        normal = -normal
    return Plane(normal, float(-normal @ centroid))


def fit_ground_plane(points, up_prior, rng, *, iterations=100, inlier_threshold=0.05,
                     max_tilt_deg=20.0, height_range=(0.5, 3.0), max_samples=4000,
                     min_inliers=200):
    """RANSAC ground-plane fit constrained by a gravity prior.

    ``points`` is (N, 3) valid camera-frame points. Candidate planes must have
    a normal within ``max_tilt_deg`` of ``up_prior`` and put the camera
    ``height_range`` above them -- which rejects walls, vehicle sides and the
    vehicle's own bonnet. Returns a refined Plane, or None if no candidate
    gathers ``min_inliers``.
    """
    if len(points) < max(3, min_inliers):
        return None
    if len(points) > max_samples:
        points = points[rng.choice(len(points), max_samples, replace=False)]
    up = np.asarray(up_prior, dtype=float)

    # Score every hypothesis at once: (iterations, 3) triples -> normals.
    a, b, c = (points[i] for i in rng.integers(0, len(points), size=(3, iterations)))
    normals = np.cross(b - a, c - a)
    norms = np.linalg.norm(normals, axis=1)
    keep = norms > 1e-9
    normals = normals[keep] / norms[keep, None]
    offsets = -np.einsum('ij,ij->i', normals, a[keep])
    normals, offsets = _orient_up(normals, offsets, up)

    cos_tilt = np.cos(np.radians(max_tilt_deg))
    ok = ((normals @ up >= cos_tilt)
          & (offsets >= height_range[0]) & (offsets <= height_range[1]))
    if not ok.any():
        return None
    normals, offsets = normals[ok], offsets[ok]

    distances = np.abs(points @ normals.T + offsets)          # (N, K)
    counts = (distances < inlier_threshold).sum(axis=0)
    best = int(np.argmax(counts))
    if counts[best] < min_inliers:
        return None

    # Two refinement passes: refit on inliers, re-select inliers, refit.
    plane = _refit(points, distances[:, best] < inlier_threshold, up)
    mask = np.abs(plane.height(points)) < inlier_threshold
    if mask.sum() < min_inliers:
        return None
    plane = _refit(points, mask, up)

    if (plane.normal @ up < cos_tilt
            or not height_range[0] <= plane.offset <= height_range[1]):
        return None
    return plane


class GroundPlaneTracker:
    """Temporal filter over per-frame plane fits.

    Smooths the plane with an exponential moving average and rejects single
    frames that jump implausibly far from the current estimate (a large
    vehicle filling the view, say). If fits keep disagreeing for
    ``max_rejections`` frames in a row, the new plane is accepted instead --
    the road itself has changed (a ramp, a crest) rather than one bad frame.
    """

    def __init__(self, alpha=0.5, max_jump_deg=5.0, max_jump_height=0.15,
                 max_rejections=5, max_hold_frames=10):
        self.alpha = alpha
        self.max_jump_cos = np.cos(np.radians(max_jump_deg))
        self.max_jump_height = max_jump_height
        self.max_rejections = max_rejections
        self.max_hold_frames = max_hold_frames
        self.plane = None
        self._rejections = 0
        self._misses = 0

    def update(self, fit):
        """Feed one frame's fit (or None); returns the current plane or None."""
        if fit is None:
            self._misses += 1
            if self._misses > self.max_hold_frames:
                self.plane = None
            return self.plane
        self._misses = 0

        if self.plane is None:
            self.plane = fit
            return self.plane

        jump = (fit.normal @ self.plane.normal < self.max_jump_cos
                or abs(fit.offset - self.plane.offset) > self.max_jump_height)
        if jump:
            self._rejections += 1
            if self._rejections < self.max_rejections:
                return self.plane
            self.plane = fit
        else:
            normal = (1 - self.alpha) * self.plane.normal + self.alpha * fit.normal
            normal /= np.linalg.norm(normal)
            offset = (1 - self.alpha) * self.plane.offset + self.alpha * fit.offset
            self.plane = Plane(normal, float(offset))
        self._rejections = 0
        return self.plane


def ground_frame(plane, forward=(0.0, 0.0, 1.0)):
    """Rotation and origin of the ground frame, expressed in the camera frame.

    Returns ``(R, t)``: R's columns are the ground frame's X (forward), Y
    (left) and Z (up) axes in camera coordinates; ``t`` is the point on the
    plane directly below the camera. A camera point p maps to the ground frame
    as ``(p - t) @ R``, which is what ``to_ground`` does.
    """
    n = plane.normal
    f = np.asarray(forward, dtype=float)
    x = f - (f @ n) * n
    x /= np.linalg.norm(x)
    y = np.cross(n, x)
    return np.column_stack((x, y, n)), -plane.offset * n


def to_ground(points, rotation, origin):
    """Transform (..., 3) camera points into the ground frame."""
    return (points - origin) @ rotation


def height_above(points, rotation, origin):
    """Height above the plane of (..., 3) camera points -- the Z component of
    to_ground alone, at a third of the cost when that is all that's needed."""
    return (points - origin) @ rotation[:, 2]


def classify(ground_points, depth, camera_height, *, obstacle_height=0.10, drop_depth=0.10,
             clearance_height=2.5, depth_noise_coeff=0.0, noise_sigmas=3.0):
    """Label (..., 3) ground-frame points by their height above the plane.

    The height tolerance grows with distance to follow stereo depth noise:
    depth error sigma_z = c * z^2, and for a ground point seen at grazing
    angle ~h/z that projects to a height error of roughly c * h * z. With
    ``depth_noise_coeff`` = 0 (perfect simulated depth) the thresholds are
    constant.
    """
    height = ground_points[..., 2]
    tolerance = noise_sigmas * depth_noise_coeff * camera_height * np.nan_to_num(depth)
    labels = np.full(height.shape, UNKNOWN, dtype=np.uint8)
    valid = np.isfinite(height)
    labels[valid] = GROUND
    labels[valid & (height > obstacle_height + tolerance)] = OBSTACLE
    labels[valid & (height > clearance_height)] = OVERHEAD
    labels[valid & (height < -(drop_depth + tolerance))] = DROP
    return labels


def mask_box(ground_points, labels, box):
    """Mark points inside a ground-frame box (x_min, x_max, y_min, y_max) as
    UNKNOWN -- used to drop the vehicle's own body (e.g. the bonnet) from view.
    """
    x, y = ground_points[..., 0], ground_points[..., 1]
    inside = (x >= box[0]) & (x <= box[1]) & (y >= box[2]) & (y <= box[3])
    labels[inside] = UNKNOWN
    return labels
