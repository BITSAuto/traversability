# D-007 · Four classes; sidewalks and grass are forbidden

- **Date:** 2026-10-02
- **Status:** Accepted (owner's answer: "Forbidden")

## Decision
The semantic model predicts road / sidewalk / terrain / other. Flat sidewalk
and terrain are **lethal**, not just costly.

## Why four classes, not binary
With a binary drivable/not-drivable model, the "enclosed by road" patch rule
would also free a flat grass median between two lanes. The patch rule
therefore applies only to "other", with a size cap.
