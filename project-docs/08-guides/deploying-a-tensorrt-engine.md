# Deploying a TensorRT engine

1. Export on the laptop (`train_student --export` or `export_model`): writes
   `m.onnx` and `m.onnx.json`.
2. Copy both to the Orin's `~/traversability_models/`.
3. Build on the Orin:
   ```bash
   /usr/src/tensorrt/bin/trtexec --onnx=m.onnx --saveEngine=m.engine --fp16
   ```
4. Keep `m.onnx.json` next to `m.engine`.
5. Run: `ros2 launch traversability d435i.launch.py semantics:=true model:=trt:$HOME/traversability_models/m.engine`
   (add `align:=true` for RGB-D models).
6. To change the default, edit `d435i.launch.py`'s `model` default and record
   a decision.
