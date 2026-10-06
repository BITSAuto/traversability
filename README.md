# traversability

Road traversability for the BITSAuto vehicle (Intel RealSense D435i):
depth geometry fused with semantic segmentation into a local occupancy grid.

- **Phase 1:** geometry only, which handles paint, paper and stains.
- **Phase 2:** adds a zero-shot semantic model and the fusion rules (grass
  and sidewalks forbidden).
- **Phase 3:** the pipeline for recording, auto-labelling and training your
  own RGB-D model, plus TensorRT deployment on the Orin.

The road is treated as a plane. Each depth frame is fit with a ground plane
(RANSAC, constrained by the IMU's gravity direction), every pixel is labelled
by its height above that plane, and the result is rasterised into a local
`nav_msgs/OccupancyGrid`. Flat things on the road — paint, a newspaper, an oil
stain — are ground no matter what they look like, which is the failure the
appearance-only YOLO model in `road_segmentation` has.

Geometry alone cannot tell road from flat grass or a flush sidewalk, so a
semantic model labels each colour pixel as road, sidewalk, terrain or other,
and `traversability_grid` fuses the two (see **Phase 2**).

## Nodes

| Executable | In | Out |
| --- | --- | --- |
| `ground_geometry` | depth image (32FC1 m or 16UC1 mm), its `CameraInfo`, `Imu` | `/traversability/ground_points` (organised `PointCloud2`, x/y/z/label in `camera_ground`), TF `<depth frame> -> camera_ground` |
| `semantic_seg` | colour image (+ registered depth for RGB-D models) | `/traversability/semantics` (mono8: 1 road, 2 sidewalk, 3 terrain, 4 other), `/traversability/semantics_overlay` |
| `traversability_grid` | `/traversability/ground_points` (+ semantics when `semantic_topic` is set) | `/traversability/grid` (`OccupancyGrid` in `camera_ground`: 0 free, 100 lethal, -1 unknown) |
| `record_frames` | colour, depth registered to colour, ground-plane TF | training frames on disk (phase 3) |
| `depth_noise` | perfect sim depth | the same with D435-like noise, sigma_z = c·z² |
| `spawn_test_scene` / `check_test_scene` | — | Webots test scene and its pass/fail check |
| `snapshot` | pipeline topics | PNG of colour, labels and grid, for headless checks |

Offline tools (need torch and transformers, so the laptop rather than the
Orin): `autolabel`, `train_student`, `export_model`, `benchmark_models`.

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
ros2 launch traversability traversability.launch.py semantics:=true                       # + SegFormer-B2
ros2 launch traversability traversability.launch.py semantics:=true model:=student:<ckpt.pt>
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

With semantics, the Orin runs a TensorRT engine; it has no torch. Engines
built there live in `~/traversability_models/`:

```bash
ros2 launch traversability d435i.launch.py semantics:=true            # SegFormer-B0 engine (default)
ros2 launch traversability d435i.launch.py semantics:=true model:=trt:$HOME/traversability_models/segformer_b2.engine
ros2 launch traversability d435i.launch.py align:=true record_dir:=$HOME/traversability_data/campus_1   # record for phase 3
```

RGB-D students also need `align:=true`, since they take the height of each
colour pixel.

### Test scene

The start pose is inside a `RoadIntersection` whose visible surface sits about
10 cm above its collision surface. Spawned objects sink into it, and there is
a 12 cm visual step at the far edge. Drive about 20 m straight ahead onto the
plain segment `road(5)` first:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 3.0}}"   # ~7 s, then Ctrl-C
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"                    # stop
ros2 run traversability spawn_test_scene
ros2 run traversability check_test_scene --ros-args -p frames:=20                 # geometry only
ros2 run traversability check_test_scene --ros-args -p frames:=10 -p mode:=fused  # with semantics
```

The scene has four flat objects that should come out free (a paint line, a
newspaper, an oil stain and a grass patch) and four obstacles that should come
out lethal (a 0.15 m brick, a 3 m × 0.15 m curb, a 0.5 m box and a 1 m
barrel), all 3.5–9 m ahead. In `fused` mode the grass must be lethal instead.
The check also counts lethal cells on the open road. To remove the scene: `ros2 run traversability spawn_test_scene --ros-args -p remove_only:=true`.

Phase 1 results (2026-10-02, re-checked 2026-10-06 after the phase 2 changes):

| Depth | Flat objects free | Obstacles lethal | False lethal on open road |
| --- | --- | --- | --- |
| Perfect (sim) | 4/4 | 4/4 | 0 |
| D435-like noise, 20 frames | 4/4 | 4/4 | 0 (plus 3–30 cells per frame smeared within 1 m of the far obstacles, which is radial depth noise of σ ≈ 0.3 m at 8 m) |

## Phase 2: semantics and fusion

`semantic_seg` runs any backend from `traversability.segmentation`. All of them
output probabilities over the same four classes:

| Spec | Backend | Use |
| --- | --- | --- |
| `hf:<model id>` | Hugging Face checkpoint (SegFormer, Mask2Former), torch | laptop, benchmarking, auto-label teacher |
| `student:<ckpt.pt>` | phase 3 student, torch | laptop |
| `trt:<engine>` | TensorRT engine built from `export_model` output | Orin; uses `libcudart` through ctypes, so there is nothing extra to install |

Source labels are mapped by name (`semantics.py`):
- **Road:** road, lane markings, crosswalks, manholes, parking, IDD "drivable fallback".
- **Sidewalk:** sidewalk, curb, pedestrian area.
- **Terrain:** vegetation, terrain, sand, water, IDD "non-drivable fallback".
- **Other:** everything else.

The fusion rules, per 10 cm cell, are in `fusion.py`:

| Geometry | Semantics | Cell |
| --- | --- | --- |
| obstacle / drop | any | lethal |
| ground | mostly road | free |
| ground | mostly sidewalk / terrain | lethal |
| ground | mostly other, ≤ 2 m² and ≥ 75 % of its border is road | free (paint, paper, stains, manholes) |
| ground | mostly other, otherwise | lethal |
| ground | outside the colour camera's view | unknown (`unlabelled_ground`) |

The grid is driven by the semantic frames. Each one is paired with the
buffered depth cloud closest to it in time, because semantics lag the cameras
by the model's latency. If semantics stop for over 1 s, the grid keeps
publishing obstacles with ground unknown. It never falls back to
geometry-only, which would show grass as free.

### Results (Webots test scene, fused mode, perfect depth)

| Model | Paint / paper / oil free | Grass lethal | Obstacles lethal | False lethal | Orin TensorRT FP16 (GPU / end-to-end / in the ROS node) |
| --- | --- | --- | --- | --- | --- |
| SegFormer-B0, Cityscapes | 3/3 | borderline: 80–89 % of cells over two runs (1 pass, 1 just under the 80 % bar) | 4/4 | 0 | 9 / 23 / 30 ms |
| SegFormer-B2, Cityscapes | 3/3 | no (0/130 cells) | 4/4 | 0 | 31 / 51 ms |
| Mask2Former Swin-L, Mapillary | 3/3 | no (0/130 cells) | 4/4 | 0 | not deployed (offline teacher) |

The fusion rule handles the patches with every model, and geometry keeps every
obstacle lethal even where a model calls it road.

**Grass is the weak point.** At 5.5 m, a 1.2 × 1.5 m grass mat lying in the
lane is called road by B2 and Mask2Former. They use the surrounding asphalt
as context. All three models got the same mat right when it was closer and
at the image edge. TensorRT output matches torch on 99.7 % of pixels or more.

## Phase 3: your own model

**Dependencies.**
- The laptop needs torch with CUDA plus
  `pip install --user transformers huggingface_hub onnx "pillow>=10"`.
  Pin `numpy==1.26.4` so `cv_bridge` keeps working, and use a pip newer
  than Ubuntu 22.04's 22.0.2, which has a resolver bug.
- The Orin needs only its TensorRT.

The workflow:

1. **Record** colour, registered depth and the ground plane while driving:
   - real camera: `d435i.launch.py align:=true record_dir:=...`;
   - sim: `ros2 run traversability record_frames --ros-args -p out_dir:=...`
     alongside the pipeline.
2. **Auto-label:** `ros2 run traversability autolabel <dir> --viz`.
   - A teacher model (Mask2Former, Mapillary) labels each pixel, then depth
     corrects it.
   - Anything above the ground becomes "other".
   - Small flat "other" blobs surrounded by flat road become **road**. That is
     what teaches the student that paint and paper are road.
   - Low-confidence pixels are ignored.
   - Check the `viz/` overlays, and correct labels by hand where it matters.
3. **Train:** `ros2 run traversability train_student --data <dirs> [--idd <IDD root>] --arch segformer-b0 --rgbd --out <dir> --export`.
   - Architectures: SegFormer-B0/B2 (starting from Cityscapes weights) or
     DINOv2-small/base with a linear head.
   - `--rgbd` adds height above ground as a fourth input channel. It is
     zero-initialised, so training starts from the RGB model's behaviour.
   - Augmentation includes pasting synthetic paper, paint and stains onto road
     pixels (labelled road), and dropping the height channel.
   - IDD has no depth, so its frames always train with the height channel
     dropped.
   - Every 10th frame is held out for validation.
4. **Compare:** `ros2 run traversability benchmark_models --data <dirs> --every 10 --models student:... hf:...`.
   It reports per-class IoU, plus flat-road recall (does the model call
   flat road, patches included, road?) and forbidden recall (does it catch
   sidewalk and terrain?).
5. **Deploy:**
   - `export_model` (or `--export`) writes ONNX and a `.json` sidecar.
   - On the Orin: `/usr/src/tensorrt/bin/trtexec --onnx=m.onnx --saveEngine=m.engine --fp16`.
   - Keep `m.onnx.json` next to the engine, then run `model:=trt:m.engine`.

Sim data for testing the pipeline comes from `tools/sim_slow_follower.py`,
which drives the city at 15 km/h, and `tools/sim_clutter_spawner.py`, which
scatters flat paper, paint, stains and grass ahead of the car. Both use
textures distinct from the test scene's.

### Results (sim, 2026-10-06)

The dataset was 480 frames from one drive around the city: 432 for training,
48 held out. The student is SegFormer-B0 RGB-D, trained for 3000 steps (25 min
on an RTX 3060).

| Model (48 held-out frames, auto-labels as reference) | mIoU | Road | Terrain | Sidewalk | Flat-road recall | Forbidden recall |
| --- | --- | --- | --- | --- | --- | --- |
| Student B0 RGB-D | 0.855 | 0.994 | 0.962 | 0.477 | 1.000 | 0.977 |
| SegFormer-B0 zero-shot | 0.583 | 0.944 | 0.459 | 0.059 | 0.978 | 0.494 |
| SegFormer-B2 zero-shot | 0.591 | 0.955 | 0.487 | 0.038 | 0.998 | 0.547 |

The reference labels come from the teacher, so this measures how well each
model matches the teacher, not accuracy against ground truth. Sidewalk barely
exists in this world (0.1 % of pixels).

**On the held-out test scene, the student passes everything except the grass
mat, like its teacher.** It inherits the teacher's error: 97 % of the grass
clutter in its training data was auto-labelled road, because Mask2Former
called it road. Geometry can only turn patches into road; it can't add
forbidden surfaces the teacher missed.

On the Orin, the student's TensorRT engine runs at 9 ms GPU / 29 ms end-to-end
and matches torch exactly. The pipeline works end to end. What a student
learns is bounded by its labels, which is why real campus data and
human-labelled IDD are the next step (see the roadmap).

## Known limitations

- **Without semantics, flat non-road surfaces count as free.** This covers
  grass, a flush sidewalk and a dirt verge. With semantics, it depends on the
  model (see the phase 2 results).
- **Auto-labels inherit the teacher's mistakes.** A student distilled from
  them can't beat the teacher on forbidden surfaces. Human labels (IDD,
  corrected campus frames) are needed for that.
- **Only colour pixels get semantics.** The colour camera's field of view
  (69°) is narrower than the depth camera's (87°), so ground in the outer
  wedges is unknown when fusing.
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

1. ~~Geometry baseline~~ (phase 1).
2. ~~Zero-shot semantics and fusion~~ (phase 2).
3. ~~Record → auto-label → train → TensorRT pipeline~~ (phase 3, validated in sim).
4. **Real data.** Record campus drives with the D435i and auto-label them.
   Spot-correct the labels, especially verges and sidewalks. Download IDD
   Segmentation (needs a free account at idd.insaan.iiit.ac.in) and run its
   `createLabels.py --id-type level3Ids`. Then train on campus data plus IDD,
   and compare against zero-shot B0 with `benchmark_models` on held-out campus
   frames.
5. **Robustness.** Use per-cell height statistics for low obstacles at range,
   and temporal accumulation of the grid (or Nav2's layers).

## Tests

```bash
python3 -m pytest test        # inside the distrobox, from this directory (torch tests skip without torch)
```
