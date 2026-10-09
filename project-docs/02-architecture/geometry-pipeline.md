# Phase 1: geometry pipeline

Per depth frame, in `ground_geometry`:

1. **Back-project** the (decimated ×2) depth image to 3D points; drop points
   outside `min_range`–`max_range`.
2. **Gravity prior**: low-pass the accelerometer (τ = 1 s) to get "down" in
   the camera frame.
3. **RANSAC plane fit** on points within `fit_min_range`–`fit_max_range`,
   accepting only planes whose normal is within `max_tilt_deg` (20°) of
   gravity and whose camera height is within `camera_height_min/max`. This
   rejects walls, vehicle sides and the bonnet.
4. **Plane tracking**: smooth the plane over time and reject single-frame
   jumps.
5. **Label** each point by signed height above the plane: ground, obstacle
   (> `obstacle_height` + margin), drop (< −`drop_depth` − margin), overhead
   (> `clearance_height`). The margin grows with distance to follow stereo
   noise: `noise_sigmas · c · h_cam · z`.
6. **Self mask**: points inside `self_mask` (vehicle body) are unknown.
7. Publish the organised labelled cloud and the TF to `camera_ground`.

In `traversability_grid` (geometry only): rasterise points into cells;
a cell with ≥ `min_obstacle_points` obstacle/drop points is lethal; ground
cells are free; ground between vertically adjacent ground pixels up to
`fill_max_gap` (1 m) apart is filled as seen; everything else is unknown.

Plain numpy (no Open3D/PCL): about 20 ms per frame on the laptop.

Why per-frame and IMU-constrained instead of a SLAM grid (RTAB-Map):
[D-003](../03-decisions/D-003-per-frame-gravity-constrained-plane-no-slam.md).
