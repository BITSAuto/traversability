# D-006 · Target hardware: Jetson Orin AGX

- **Date:** 2026-10-02
- **Status:** Accepted (owner's answer)

The cart's computer is a Jetson Orin AGX (Jazzy). Its budget allows
mid-size models (SegFormer-B2-class) in real time with TensorRT FP16, so the
lightest networks weren't required. The whole pipeline must fit the
camera's frame time, measured end to end on the Orin.
