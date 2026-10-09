# Laptop Python environment

**Verified** (2026-10-06), inside the `ubuntu22` distrobox:
- `transformers` 5.18, `onnx`, `huggingface_hub`, Pillow 12.3 in `~/.local`.
- Ubuntu 22.04's pip 22.0.2 has a resolver bug; pip was upgraded to 25.3 in
  the user site.
- **numpy must stay at 1.26.4**: numpy 2 breaks `cv_bridge` on Humble.
- torch with CUDA on an RTX 3060: a 3000-step SegFormer-B0 RGB-D run takes
  about 25 min.
- Build with `PYTHONNOUSERSITE=1 colcon build --symlink-install` (user-site
  setuptools breaks `ament_python`).
