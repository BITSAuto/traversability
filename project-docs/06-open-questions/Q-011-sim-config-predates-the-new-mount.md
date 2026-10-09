# Q-011 · `config/tesla_sim.yaml` predates the new camera mount

- **Opened:** 2026-10-09 · **Status:** Open · **Priority:** low

Its comments describe the old ~1.24 m mount and a bonnet out to ~2.2 m;
since 2026-10-08 the camera is at 1.52 m and the bonnet hides the road to
~2.7 m. The values (`fit_min_range` 2.0, `self_mask` up to x = 2.3) worked in
every `cart_driver` run since, but re-derive them and fix the comments.
