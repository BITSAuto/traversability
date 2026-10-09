# D-018 · Compute the RGB-D height input at reduced resolution

- **Date:** 2026-10-08
- **Status:** Accepted ([PR #2](https://github.com/BITSAuto/traversability/pull/2))

With the sim loading the CPU, computing the full-resolution height image
took ~100 ms per frame; semantics arrived 0.67 s late and mostly couldn't be
paired. Now computed at half resolution (`height_decimation` 2; the model
sees ~1024×576 anyway) using only the height component
(`geometry.height_above`, ~3× cheaper). Latency 0.67 → 0.21 s.
