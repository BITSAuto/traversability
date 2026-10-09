# Phase 1: geometry-only test scene

2026-10-02, rechecked 2026-10-06 after phase 2.

| Depth | Flat objects free | Obstacles lethal | False lethal on open road |
| --- | --- | --- | --- |
| Perfect (sim) | 4/4 | 4/4 | 0 (5/5 frames passed) |
| D435-like noise, 20 frames | 4/4 | 4/4 | 0 (20/20 frames passed), plus 3–30 cells per frame smeared within 1 m of far obstacles (radial noise σ ≈ 0.3 m at 8 m) |

Measured heights: paint, newspaper, oil and grass ~3 mm; brick and curb
0.13 m; box 0.48 m. Known weak spots: the flat grass patch is free (geometry
can't tell), the 13 cm curb at 4–7 m under noise is only partly detected
(~11 of 90 cells).
