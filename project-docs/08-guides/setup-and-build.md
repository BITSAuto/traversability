# Setup and build

## Laptop (Humble, distrobox)
```bash
cd ~/ros2_ws/src && git clone https://github.com/BITSAuto/traversability.git
cd ~/ros2_ws && PYTHONNOUSERSITE=1 colcon build --symlink-install --packages-select traversability
```
For phases 2–3 (torch tools): torch with CUDA, then
`pip install --user transformers huggingface_hub onnx "pillow>=10"`; keep
`numpy==1.26.4`; use a pip newer than 22.0.2.

## Orin (Jazzy)
`realsense2_camera`, `cv_bridge`, numpy and TensorRT are already there. Clone,
build with `colcon build`, and copy engines to `~/traversability_models/`.

## Tests
```bash
cd ~/ros2_ws/src/traversability && python3 -m pytest test   # torch tests skip without torch
```
