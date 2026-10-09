# Campus results (2026-10-07)

144 frames from the 2026-10-01 bag; trained on the first 75 % (108 frames),
scored on the last 25 % (36 frames); reference = auto-labels.

| Model | mIoU | Road | Sidewalk | Terrain | Other | Forbidden recall | Laptop ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Campus student B0 RGB-D | 0.865 | 0.949 | 0.679 | 0.892 | 0.940 | 0.931 | 26 |
| Campus student B0 RGB | 0.863 | 0.951 | 0.673 | 0.890 | 0.939 | 0.923 | 22 |
| SegFormer-B0 zero-shot | 0.698 | 0.929 | 0.315 | 0.694 | 0.856 | 0.902 | 25 |
| SegFormer-B2 zero-shot | 0.681 | 0.933 | 0.225 | 0.698 | 0.867 | 0.861 | 51 |
| Sim-trained student B0 RGB-D | 0.468 | 0.878 | 0.011 | 0.459 | 0.526 | 0.808 | 25 |

- 108 real frames help a lot, especially for sidewalk/curb and terrain.
- Sim training doesn't transfer.
- The height channel barely matters at this data size.
- Same route, light and day as training; labels unchecked. Expect lower on
  new routes. Zero-shot B0 stays the default ([D-014](../03-decisions/D-014-default-model-zero-shot-segformer-b0.md)).

Qualitatively (held-out frames 110, 126, 140): depth alone frees the paved
parking area and footpath (flat); both models block them as sidewalk; on
frame 110 zero-shot B0 calls part of the paving road while the campus student
blocks it. Road ahead free; curbs, hedges and the scooter lethal in every
version.

Checkpoints: `~/traversability_data/students/b0_rgbd_campus/`,
`b0_rgb_campus/` (laptop).
