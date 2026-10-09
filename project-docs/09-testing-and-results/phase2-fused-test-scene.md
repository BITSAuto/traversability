# Phase 2: fused test scene (perfect depth)

2026-10-06.

| Model | Paint / paper / oil free | Grass lethal | Obstacles lethal | False lethal |
| --- | --- | --- | --- | --- |
| SegFormer-B0, Cityscapes | 3/3 | borderline: 80–89 % of cells over two runs (one pass, one just under the 80 % bar) | 4/4 | 0 |
| SegFormer-B2, Cityscapes | 3/3 | no (0/130 cells) | 4/4 | 0 |
| Mask2Former Swin-L, Mapillary | 3/3 | no (0/130 cells) | 4/4 | 0 |
| Sim student B0 RGB-D | 3/3 | no | 4/4 | 0 |

The patch rule works with every model; geometry keeps every obstacle lethal
even where a model calls it road.
