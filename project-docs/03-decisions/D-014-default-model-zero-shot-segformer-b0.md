# D-014 · Default model: zero-shot SegFormer-B0

- **Date:** 2026-10-06, confirmed 2026-10-07
- **Status:** Accepted (revisit when there is more campus data)

B2 wasn't more accurate on campus frames (mIoU 0.68 vs 0.70) and is twice as
slow on the Orin (51 vs 23 ms). The campus-trained student scores higher
(0.865) but on only 108 frames from one route, one evening, judged against
auto-labels, so it isn't trusted as the default yet. The sim-trained student
doesn't transfer to real roads (0.47).
