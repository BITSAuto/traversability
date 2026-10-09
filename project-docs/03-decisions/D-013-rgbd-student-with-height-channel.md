# D-013 · RGB-D students take height above ground, zero-initialised

- **Date:** 2026-10-06
- **Status:** Accepted

Height above the fitted ground plane (not raw depth) is the 4th input: it
directly encodes "is this on the ground?", where raw depth mostly encodes
distance. The extra input weights start at zero so training begins from the
RGB model's behaviour; augmentation randomly drops the channel so the model
also works without it (and IDD, which has no depth, can be mixed in).

Result so far: at 108 real frames the height channel barely matters
(mIoU 0.865 RGB-D vs 0.863 RGB).
