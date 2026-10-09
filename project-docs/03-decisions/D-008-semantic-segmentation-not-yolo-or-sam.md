# D-008 · Per-pixel semantic segmentation; SAM/DINO only where they fit

- **Date:** 2026-10-02
- **Status:** Accepted

## Decision
Use semantic segmentation (one class per pixel): SegFormer (Cityscapes) as
the main zero-shot candidates and Mask2Former Swin-L (Mapillary Vistas) as
the accuracy reference and auto-labeller.

## Why not YOLO
YOLO11-seg is instance segmentation: it treats road as an object, drops
low-confidence regions (`conf=0.85`) and returns low-resolution masks. Road
is a region, not an object.

## Why not SAM, Grounding DINO or open-vocabulary models as the main model
- **SAM/SAM2:** class-less masks; it would still cut the newspaper out as its
  own object. Useful for offline labelling.
- **Grounding DINO / Grounded-SAM:** objects, not regions; weak at road vs
  sidewalk; too slow. Useful for finding rare things in recordings.
- **DINOv2/v3:** features, not a segmenter; strong as a **student backbone**
  with a trained head (implemented as `train_student --arch dinov2-*`).
- **Open-vocabulary (CLIP-based):** weaker on fine distinctions, slow.

## Licences
SegFormer's official weights are under NVIDIA's non-commercial licence (fine
for research); Mask2Former is permissive.
