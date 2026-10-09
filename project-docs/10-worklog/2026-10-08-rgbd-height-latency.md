# 2026-10-08 · RGB-D height at reduced resolution (PR #2)

**Who:** project owner, with Claude Code
**Branch / PR:** `perf/rgbd-height`, [PR #2](https://github.com/BITSAuto/traversability/pull/2) (merged `f5fed65`)

Found while testing `cart_driver` in the sim: semantics arrived 0.67 s late.
Half-resolution height and `height_above` brought it to 0.21 s (M-10,
[D-018](../03-decisions/D-018-rgbd-height-at-reduced-resolution.md)). Also
found `cart_driver`'s `params` launch argument overriding ours (M-11; fixed
in cart_driver).
