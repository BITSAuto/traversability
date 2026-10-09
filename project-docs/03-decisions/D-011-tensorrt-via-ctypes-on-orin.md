# D-011 · TensorRT on the Orin through `libcudart` and ctypes

- **Date:** 2026-10-06
- **Status:** Accepted

The Orin has TensorRT but no torch and no CUDA Python packages. The
`trt:` backend loads engines with the TensorRT Python API and manages device
memory through `libcudart` via ctypes, so nothing extra has to be installed
there. Exported ONNX graphs bake in normalisation, softmax and class
aggregation.
