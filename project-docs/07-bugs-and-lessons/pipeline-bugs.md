# Pipeline bugs

## M-01: Semantics were paired with the wrong depth cloud
- **Found:** 2026-10-06
- **Symptom:** fused cells misplaced; few fused grids.
- **Root cause:** semantics arrive ~0.35 s after the camera frame (laptop);
  pairing with the latest cloud mismatched them.
- **Fix:** grid driven by semantic frames, each paired with the buffered cloud
  closest in time ([D-010](../03-decisions/D-010-semantics-drive-the-grid-no-geometry-only-fallback.md)).

## M-02: Repeated camera stamps produced duplicate semantic frames
- **Found:** 2026-10-06
- **Symptom:** the same cloud fused several times.
- **Fix:** drop semantic frames with a stamp already processed.

## M-03: A geometry-only fallback would have freed grass
- **Found:** 2026-10-06 (design review)
- **Fix:** when semantics stop for 1 s, ground becomes unknown, not free.

## M-04: RealSense launch arguments weren't scoped
- **Found:** 2026-10-02 (`da7ab47`)
- **Cause:** arguments declared in `d435i.launch.py` were visible to the
  included `realsense2_camera` launch (launch arguments are global).
- **Fix:** include it inside a `GroupAction` with scoped arguments. The same
  class of bug later hit `cart_driver` (M-11).

## M-05: Ctrl-C under `ros2 launch` on Jazzy printed "process has died, exit code -2"
- **Found:** 2026-10-02
- **Cause:** harmless Jazzy reporting for Python nodes that did shut down.
- **Fix:** quietened in `da7ab47`.
