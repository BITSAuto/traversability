# Hardware and environment

| Item | Details |
| --- | --- |
| Camera | Intel RealSense D435i via `realsense2_camera`: depth 848×480 (16UC1 mm), colour 1280×720, accelerometer. USB 3 needed for 30 fps; on USB 2 use `fps:=15` |
| Camera mount on the cart | ~1.52 m above the road, centred, ~9° down (measured from the 2026-10-01 bag). Not yet permanently fixed, so the D435i config has no self-mask and `camera_height_min` 0.2 m (hand-held testing) |
| Cart computer | Jetson Orin AGX, Ubuntu 24.04, ROS 2 **Jazzy**, TensorRT **10.16**, **no torch**. `trtexec` at `/usr/src/tensorrt/bin/trtexec`. Engines live in `~/traversability_models/` on the Orin |
| Laptop | ROS 2 **Humble** in the `ubuntu22` distrobox; RTX 3060; torch with CUDA; `transformers` 5.18, `onnx`, `huggingface_hub`, Pillow 12.3, pip 25.3 in the distrobox's `~/.local`; **numpy pinned 1.26.4** (newer breaks `cv_bridge`) |
| Simulator | tesla_sim (Webots) on the laptop |

## Where data and models live (not in git)

| What | Where | Size |
| --- | --- | --- |
| Repaired campus bag (2026-10-01) | laptop `~/traversability_data/campus_bag_20261001/bag_0.mcap` | 16 GB |
| Campus frames (144, auto-labelled) | laptop `~/traversability_data/campus_20261001/` (also produced on the Orin) | 197 MB |
| Sim training frames (480) | laptop `~/traversability_data/sim_train/` (hard links into `sim_drive_3`) | — |
| Exported zero-shot models (ONNX) | laptop `~/traversability_data/models/segformer_b0.onnx`, `segformer_b2.onnx` (+ `.json` sidecars) | 120 MB |
| Students | laptop `~/traversability_data/students/b0_rgbd_sim`, `b0_rgbd_campus`, `b0_rgb_campus` (`best.pt`, `best.onnx`, `.json`, `log.csv`) | 129 MB |
| TensorRT engines | Orin `~/traversability_models/` (B0, B2, students) | — |

These exist on one laptop and the Orin only. A shared home for datasets and
models is an open question ([Q-010](../06-open-questions/Q-010-shared-storage-for-data-and-models.md)).
