# Integration bugs (with tesla_sim and cart_driver, 2026-10-08)

## M-10: The RGB-D height image made semantics too stale to fuse
- **Symptom:** under `cart_driver`'s sim launch, the fused grid stayed mostly
  unknown.
- **Root cause:** computing the full-resolution height image took ~100 ms
  per frame with the sim loading the CPU; semantics arrived 0.67 s late.
- **Fix:** half resolution, height component only (PR #2,
  [D-018](../03-decisions/D-018-rgbd-height-at-reduced-resolution.md)); 0.21 s.

## M-11: An including launch's `params` argument replaced this package's config
- **Symptom:** the bonnet was lethal in every grid when perception ran under
  `cart_driver`'s launch.
- **Root cause:** `cart_driver`'s `sim.launch.py` declared its own `params`
  argument. Launch arguments are global, so the included
  `traversability.launch.py` read `cart_driver`'s file as its config and lost
  its bonnet mask.
- **Fix:** `cart_driver` renamed its argument to `cart_params`.
- **Rule:** when including this package's launch files, don't declare an
  argument called `params`, `model`, `semantics` or `noise` unless you mean
  to set ours.
