# Q-009 · Configuration for the mounted camera

- **Opened:** 2026-10-02 · **Status:** Open · **Priority:** medium

`config/d435i.yaml` has no `self_mask` and `camera_height_min` 0.2 m (for
hand-held tests). Once the mount is fixed: set the body mask, raise
`camera_height_min` (~1.2 m), and check `fit_min_range` against where the
cart's front hides the road.
