# Models and datasets

| Model | Pretrained on | Role here | Notes |
| --- | --- | --- | --- |
| SegFormer-B0 (`nvidia/segformer-b0-finetuned-cityscapes-*`) | ImageNet-1k, then Cityscapes (2,975 images, 50 German/Swiss cities, 19 classes) | **default** on the Orin, zero-shot | NVIDIA non-commercial licence |
| SegFormer-B2 (`nvidia/segformer-b2-finetuned-cityscapes-1024-1024`) | Cityscapes | default in the sim launch; benchmark | not better than B0 on campus, 2× slower |
| Mask2Former Swin-L (`facebook/mask2former-swin-large-mapillary-vistas-semantic`) | Mapillary Vistas (~18k images worldwide, 65 classes incl. lane marking, crosswalk, manhole, curb, terrain) | auto-labelling teacher, accuracy reference | too slow for real time |
| DINOv2-small/base + linear head | self-supervised features | student option (`--arch`) | not yet compared on campus data |
| Our students (SegFormer-B0, RGB or RGB-D) | Cityscapes B0 + our auto-labels | campus candidate | see [09](../09-testing-and-results/README.md) |

**Verified behaviour on our data**
- Every model handles the patch case once fused with geometry.
- A 1.2 × 1.5 m grass mat lying in the sim lane at 5.5 m: B2 and Mask2Former
  call it road (asphalt context); B0 mostly catches it (80–89 % of cells);
  all three got it right when closer and at the image edge.
- 97 % of grass clutter in the sim training data was auto-labelled road,
  because the teacher called it road.
- Sidewalk barely exists in the sim world (0.1 % of pixels).
- Sim-trained models don't transfer to real campus frames (mIoU 0.47).

**Datasets**
- **IDD (India Driving Dataset)** — the most relevant: Indian roads, explicit
  drivable / non-drivable fallback classes, human labels. Needs a free
  account at idd.insaan.iiit.ac.in (the owner must create it); then run its
  `createLabels.py --id-type level3Ids` and pass `--idd`. Not downloaded yet.
- BDD100K and Mapillary Vistas are possible additions.
- Few IDD-trained checkpoints are publicly available.
