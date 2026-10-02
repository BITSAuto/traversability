# traversability

Depth-based road traversability for the BITSAuto vehicle (Intel RealSense
D435i). Phase 1 of the road-segmentation plan: geometry only, no learning.

The road is treated as a plane. Each depth frame is fit with a ground plane
(RANSAC, constrained by the IMU's gravity direction), every pixel is labelled
by its height above that plane, and the result is rasterised into a local
`nav_msgs/OccupancyGrid`. Flat things on the road — paint, a newspaper, an oil
stain — are ground no matter what they look like, which is the failure the
appearance-only YOLO model in `road_segmentation` has.

Geometry alone cannot tell road from flat grass or a flush sidewalk. Phase 2
adds a semantic model and fuses it in `grid_node` (see **Roadmap**).

## Nodes

| Executable | In | Out |
| --- | --- | --- |
| `ground_geometry` | depth image (32FC1 m or 16UC1 mm), its `CameraInfo`, `Imu` | `/traversability/ground_points` (organised `PointCloud2`, x/y/z/label in `camera_ground`), TF `<depth frame> -> camera_ground` |
| `traversability_grid` | `/traversability/ground_points` | `/traversability/grid` (`OccupancyGrid` in `camera_ground`: 0 free, 100 lethal, -1 unknown) |
| `depth_noise` | perfect sim depth | the same with D435-like noise, sigma_z = c·z² |
| `spawn_test_scene` / `check_test_scene` | — | Webots test scene and its pass/fail check |

`camera_ground` sits on the road directly below the camera: X forward, Y
left, Z up. Point labels: 0 unknown/masked, 1 ground, 2 obstacle, 3 drop,
4 overhead (above `clearance_height`).

The core maths is in plain numpy (`geometry.py`, `grid.py`) with unit tests,
so it runs unchanged on the Orin and can be profiled outside ROS.

### Key parameters (`ground_geometry`)

| Parameter | Default | Meaning |
| --- | --- | --- |
| `obstacle_height` / `drop_depth` | 0.08 / 0.10 m | height above / below the plane that counts as obstacle / drop |
| `depth_noise_coeff`, `noise_sigmas` | 0.005, 2 | thresholds grow by `noise_sigmas · c · h_cam · z` to follow stereo noise; set c = 0 for perfect depth |
| `max_tilt_deg`, `camera_height_min/max` | 20°, 0.5–3 m | plane-fit constraints that reject walls, vehicle sides and the bonnet |
| `fit_min_range`, `fit_max_range` | 1–8 m | only these depths are used to fit the plane |
| `self_mask` | off | ground-frame box `[x_min, x_max, y_min, y_max]` hiding the vehicle's own body |
| `decimation` | 2 | pixel subsampling (848×480 → 424×240) |

`config/tesla_sim.yaml` holds the Webots values (bonnet mask, no noise
margin). The real vehicle needs its own file once the camera mount is fixed.

## Running in the Webots sim

```bash
distrobox enter ubuntu22 -- ~/ros2_ws/scripts/run_tesla_sim.sh
# second terminal, same ROS_DOMAIN_ID, inside the distrobox with the workspace sourced:
ros2 launch traversability traversability.launch.py              # perfect sim depth
ros2 launch traversability traversability.launch.py noise:=true  # D435-like noise
```

To look at it, add an RViz `Map` display on `/traversability/grid` and a
`PointCloud2` display on `/traversability/ground_points` (colour by `label`),
with fixed frame `camera_ground`.

## Running on a real D435i (Orin)

```bash
source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash
ros2 launch traversability d435i.launch.py              # driver + pipeline
ros2 launch traversability d435i.launch.py rviz:=true   # ... with RViz (needs a display)
ros2 run traversability snapshot                        # headless: writes traversability_snapshot.png
```

The launch file starts `realsense2_camera` with 848×480 depth and colour, plus
the accelerometer. Use a USB 3 port. On USB 2, pass `fps:=15`. Parameters are
in `config/d435i.yaml`. There is no self-mask yet, and `camera_height_min`
is 0.2 m to allow hand-held testing. Once the camera has a fixed mount on the
vehicle, set both.

`snapshot` saves the colour image, the per-pixel labels and the grid side by
side, and logs the label counts and the ground-height spread. Use it to check
results over SSH.

### Test scene

The start pose is inside a `RoadIntersection` whose visible surface sits about
10 cm above its collision surface. Spawned objects sink into it, and there is
a 12 cm visual step at the far edge. Drive about 20 m straight ahead onto the
plain segment `road(5)` first:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 3.0}}"   # ~7 s, then Ctrl-C
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"                    # stop
ros2 run traversability spawn_test_scene
ros2 run traversability check_test_scene --ros-args -p frames:=20
```

The scene has four flat objects that should come out free (a paint line, a
newspaper, an oil stain and a grass patch) and four obstacles that should come
out lethal (a 0.15 m brick, a 3 m × 0.15 m curb, a 0.5 m box and a 1 m
barrel), all 3.5–9 m ahead. The check also counts lethal cells on the open
road. To remove the scene: `ros2 run traversability spawn_test_scene --ros-args -p remove_only:=true`.

Results on 2026-10-02:

| Depth | Flat objects free | Obstacles lethal | False lethal on open road |
| --- | --- | --- | --- |
| Perfect (sim) | 4/4 | 4/4 | 0 |
| D435-like noise, 20 frames | 4/4 | 4/4 | 0 (plus 3–30 cells per frame smeared within 1 m of the far obstacles, which is radial depth noise of σ ≈ 0.3 m at 8 m) |

## Known limitations

- **Flat non-road surfaces count as free.** This covers grass, a flush
  sidewalk, a dirt verge, and the grass patch in the test scene. Phase 2's
  semantics have to forbid them.
- **Low obstacles at range under noise.** With real D435 noise the height
  margin at 5–7 m is about 0.15 m. A 13 cm curb there is detected only
  sparsely (about 11 of 90 cells in the noisy run). Per-cell statistics
  instead of per-point thresholds would help. On the Orin, a learned
  RGB-D model is the real fix.
- **Single plane.** The plane fit assumes the road is locally planar out to
  `fit_max_range`. Crests, dips and steep cambers beyond that will mislabel.
- **Drops are untested in the sim.** Webots roads can't have holes cut in
  them. Gaps of more than 1 m between consecutive ground pixels stay unknown
  rather than being filled as free (`fill_max_gap`).
- **The IMU gravity prior is low-pass filtered** (τ = 1 s). Hard braking
  tilts it briefly, which is why the tilt tolerance is 20°. The plane
  tracker smooths the result and rejects single-frame jumps.

## Roadmap

1. ~~Geometry baseline in Webots~~ (this package).
2. Run a multi-class semantic model zero-shot (SegFormer / PIDNet with
   Cityscapes or Mapillary weights, mapped to road / sidewalk / vegetation /
   other). Fuse it in `grid_node`:
   - Geometry obstacle → lethal.
   - Road → free.
   - "Other" that is small and enclosed by road → free.
   - Sidewalk or vegetation → lethal.
   - "Other" that is large → lethal.
   For this, `ground_geometry` should run on depth registered to the RGB
   image (`/vehicle/range_finder/image_registered`).
3. Fine-tune on IDD, Webots ground-truth segmentation, and campus D435i
   recordings auto-labelled with SAM2 plus geometry. Then move to RGB-D
   (ESANet / DFormer with a height-above-ground channel).
4. Deploy with TensorRT on the Orin AGX and measure an end-to-end latency
   budget.

## Tests

```bash
python3 -m pytest test        # inside the distrobox, from this directory
```
