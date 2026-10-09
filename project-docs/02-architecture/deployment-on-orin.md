# Deployment on the Orin

- The Orin runs Jazzy and TensorRT 10.16 and has **no torch**. Everything in
  the ROS pipeline is numpy/cv2 plus the TensorRT backend, which loads
  `libcudart` through ctypes.
- Build engines on the Orin itself (engines aren't portable across GPUs or
  TensorRT versions): `/usr/src/tensorrt/bin/trtexec --onnx=m.onnx --saveEngine=m.engine --fp16`.
  Keep `m.onnx.json` next to the engine.
- Engines live in `~/traversability_models/`. The D435i launch defaults to
  the SegFormer-B0 engine.
- TensorRT output matches torch on ≥ 99.7 % of pixels (B0, B2) and exactly
  for the sim student.
- Latency: SegFormer-B0 9 ms GPU / 23 ms end-to-end / ~30 ms in the ROS node;
  B2 31 / 51 ms; full pipeline on bag replay ~46 ms (B0) and 46–53 ms
  (campus RGB-D student). See [orin-latency.md](../09-testing-and-results/orin-latency.md).
- Use a separate `ROS_DOMAIN_ID` for tests on the Orin so other running
  stacks on domain 0 aren't disturbed (77 was used on 2026-10-02).
- Tests on the Orin: `python3 -m pytest test` passes with the torch test
  skipped.
