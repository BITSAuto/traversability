# Interfaces

## Topics

| Topic | Type | Publisher | Notes |
| --- | --- | --- | --- |
| `/traversability/ground_points` | `PointCloud2` (organised; x, y, z, label) | `ground_geometry` | in `camera_ground` |
| `/traversability/semantics` | `Image` mono8 | `semantic_seg` | 1 road, 2 sidewalk, 3 terrain, 4 other |
| `/traversability/semantics_overlay` | `Image` | `semantic_seg` | for viewing |
| `/traversability/grid` | `OccupancyGrid` | `traversability_grid` | `camera_ground`; 0 free, 100 lethal, −1 unknown |
| TF `<depth frame> → camera_ground` | | `ground_geometry` | updated per frame |

Inputs (sim / real): depth `/vehicle/range_finder/image` /
`/camera/camera/depth/image_rect_raw`; colour `/vehicle/camera/image_color` /
`/camera/camera/color/image_raw`; registered depth
`/vehicle/range_finder/image_registered` /
`/camera/camera/aligned_depth_to_color/image_raw`; IMU `/vehicle/imu` /
`/camera/camera/accel/sample`.

## Key parameters

`ground_geometry`: `obstacle_height` 0.08 m, `drop_depth` 0.10 m,
`clearance_height` 2.5 m, `depth_noise_coeff` 0.005 (0 for perfect sim
depth), `noise_sigmas` 2, `max_tilt_deg` 20°, `camera_height_min/max`
0.5–3 m, `fit_min_range`/`fit_max_range` 1–8 m, `ransac_iterations` 100,
`inlier_threshold` 0.05 m, `decimation` 2, `min_range`/`max_range`
0.3–10 m, `self_mask` `[x_min, x_max, y_min, y_max]` in `camera_ground`,
`imu_filter_tau` 1 s.

`traversability_grid`: `x_min/x_max/y_min/y_max`, `resolution` (sim 0.1 m,
D435i 0.05 m), `min_obstacle_points` 3, `fill_max_gap` 1.0 m,
`semantic_topic` (empty = geometry only), `semantic_max_age` 0.1 s (max stamp
gap to pair a semantic frame with a cloud), `semantic_timeout` 1.0 s,
`max_patch_area` 2.0 m², `enclosure_fraction` 0.75, `enclosure_margin` 2
cells, `unlabelled_ground` `unknown`.

`semantic_seg`: `model` (`hf:<id>`, `student:<ckpt.pt>`, `trt:<engine>`),
`input_width/height` 1024×576, `min_confidence`, `height_decimation` 2
(RGB-D height computed at half resolution).

`record_frames`: `out_dir`, `min_interval` 0.5 s, `max_frames`, `max_skew`
0.05 s.

Per-setup values: `config/tesla_sim.yaml`, `config/d435i.yaml`.

## Launch arguments

| `traversability.launch.py` | Default |
| --- | --- |
| `params` | `config/tesla_sim.yaml` |
| `noise` | `false` |
| `semantics` | `false` |
| `model` | `hf:nvidia/segformer-b2-finetuned-cityscapes-1024-1024` |

| `d435i.launch.py` | Default |
| --- | --- |
| `params` | `config/d435i.yaml` |
| `camera` | `true` (false: replay a bag instead) |
| `rviz` | `false` |
| `fps` | `30` |
| `semantics` | `false` |
| `model` | `trt:~/traversability_models/segformer_b0.engine` |
| `align` | `false` (true for RGB-D models and recording) |
| `record_dir` | empty (set to record frames) |

**Launch arguments are global.** A launch file that includes
`traversability.launch.py` must not declare its own argument called
`params`, or it silently replaces this one ([integration-bugs.md](../07-bugs-and-lessons/integration-bugs.md)).
