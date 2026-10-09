# D-005 · Height thresholds widen with distance

- **Date:** 2026-10-02
- **Status:** Accepted

Stereo depth error grows with the square of distance. The obstacle/drop
margin is `noise_sigmas · c · h_cam · z` on top of the base thresholds
(0.08 m up, 0.10 m down), with `c` = 0.005 for the D435i and 0 for perfect
sim depth. A fixed threshold would flag distant road as obstacles or miss
near curbs.
