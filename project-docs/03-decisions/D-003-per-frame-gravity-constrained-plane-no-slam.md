# D-003 · Per-frame, gravity-constrained plane fit; no SLAM

- **Date:** 2026-10-02
- **Status:** Accepted

## Decision
Re-fit the road plane every frame with RANSAC, rejecting planes more than 20°
from the IMU's gravity direction or at an implausible camera height, and
track it over time. No odometry, no map.

## Compared with RTAB-Map's occupancy grid (asked 2026-10-02)
RTAB-Map also separates ground from obstacles geometrically (height bands or
normals) and would also treat a newspaper as ground. Differences:

| | This package | RTAB-Map |
| --- | --- | --- |
| Memory over time | none (per frame) | accumulates; fills occlusions, averages noise |
| Needs odometry | no | yes (fragile visual odometry outdoors) |
| Where the ground is | re-fitted every frame with gravity; no mount calibration | fixed height bands or angle; needs an accurate mount and a flat world |
| Threshold vs distance | widens with D435 noise | fixed |
| Semantics | built in (phase 2) | not native |
| Weight | ~20 ms/frame | full SLAM |

For geometry alone RTAB-Map would do about as well. This package's value is
odometry independence, per-frame adaptation and the semantics fusion. They
can coexist; memory over time is now handled by `cart_driver`'s local map.
A head-to-head baseline was never run ([Q-012](../06-open-questions/Q-012-rtabmap-baseline.md)).
