# Sim-trained student (2026-10-06)

Data: 480 frames from one drive around the sim city with flat clutter and
grass scattered ahead (`tools/sim_slow_follower.py`,
`tools/sim_clutter_spawner.py`); 432 train, 48 held out (every 10th).
SegFormer-B0 RGB-D, 3000 steps, 25 min on an RTX 3060.
Checkpoint: `~/traversability_data/students/b0_rgbd_sim/` (laptop).

| Model (48 held-out frames, vs auto-labels) | mIoU | Road | Terrain | Sidewalk | Flat-road recall | Forbidden recall |
| --- | --- | --- | --- | --- | --- | --- |
| Student B0 RGB-D | 0.855 | 0.994 | 0.962 | 0.477 | 1.000 | 0.977 |
| SegFormer-B0 zero-shot | 0.583 | 0.944 | 0.459 | 0.059 | 0.978 | 0.494 |
| SegFormer-B2 zero-shot | 0.591 | 0.955 | 0.487 | 0.038 | 0.998 | 0.547 |

This measures agreement with the teacher, not accuracy. On the held-out test
scene it passes everything except the grass mat, like its teacher. Used as
the perception model for `cart_driver`'s sim tests
([D-019](../03-decisions/D-019-sim-trained-student-for-sim-driving-tests.md)).
