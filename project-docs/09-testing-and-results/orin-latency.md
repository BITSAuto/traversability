# Orin latency (TensorRT FP16)

| Model | GPU | End to end | In the ROS node / pipeline | Date |
| --- | --- | --- | --- | --- |
| SegFormer-B0 | 9 ms | 23 ms | ~30 ms (≈33 Hz) | 2026-10-06 |
| SegFormer-B2 | 31 ms | 51 ms | — | 2026-10-06 |
| Sim student B0 RGB-D | 9 ms | 29 ms | — | 2026-10-06 |
| SegFormer-B0, full pipeline on bag replay | — | — | ~46 ms per frame (bag replay sharing the CPU) | 2026-10-07 |
| Campus student B0 RGB-D, full pipeline on bag replay | — | — | 46–53 ms | 2026-10-07 |

TensorRT matches torch on ≥ 99.7 % of pixels (exactly for the sim student).
Phase 1 geometry alone: ~20 ms per frame (laptop, numpy).
