# Phase 2: semantics and fusion

## Backends (`segmentation.py`)
All map an image (plus height above ground for RGB-D students) to
probabilities over road / sidewalk / terrain / other.

| Spec | Backend | Where |
| --- | --- | --- |
| `hf:<model id>` | Hugging Face SegFormer or Mask2Former (torch) | laptop: development, benchmarks, teacher |
| `student:<ckpt.pt>` | our trained student (torch) | laptop |
| `trt:<engine>` | TensorRT engine via `libcudart` + ctypes | Orin (no torch, no CUDA Python needed) |

Exported ONNX graphs take raw RGB (float32 0–255, NCHW) plus optional height
in metres, with normalisation, softmax and label aggregation baked in.

## Class mapping (`semantics.py`, by label name)
- **Road:** road, lane markings, crosswalks, manholes, parking, IDD
  "drivable fallback".
- **Sidewalk:** sidewalk, curb, pedestrian area.
- **Terrain:** vegetation, terrain, sand, water, IDD "non-drivable fallback".
- **Other:** everything else.

## Fusion (`fusion.py`), per cell

| Geometry | Semantics | Cell |
| --- | --- | --- |
| obstacle / drop | any | lethal (geometry always wins) |
| ground | mostly road | free |
| ground | mostly sidewalk / terrain | lethal |
| ground | mostly other, ≤ 2 m², ≥ 75 % of its border road | free (patch rule) |
| ground | mostly other, otherwise | lethal |
| ground | outside the colour camera's view | unknown |

Each depth point is projected into the colour camera to take that pixel's
class. Patch candidates are connected components; the border ring is
`enclosure_margin` (2) cells wide.

## Timing
- The grid is **driven by semantic frames**. Each is paired with the
  buffered depth cloud closest in time (within `semantic_max_age`), because
  semantics lag the camera by the model's latency.
- Repeated camera stamps produced duplicate semantic frames that fused the
  same cloud several times; duplicates are dropped.
- With no semantics for `semantic_timeout` (1 s), the grid publishes from
  clouds alone: obstacles lethal, **ground unknown**. It never falls back to
  geometry-only "flat = free", which would make grass drivable
  ([D-010](../03-decisions/D-010-semantics-drive-the-grid-no-geometry-only-fallback.md)).
- For RGB-D models, the height image is computed at half resolution with
  `geometry.height_above` (0.67 s → 0.21 s latency in the sim,
  [D-018](../03-decisions/D-018-rgbd-height-at-reduced-resolution.md)).
