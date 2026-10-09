# D-017 · Validate on a later stretch of the drive, not every n-th frame

- **Date:** 2026-10-07
- **Status:** Accepted (`1134e58`)

Neighbouring frames of a recording are near-duplicates, so every-10th-frame
validation flatters a model. `train_student --val-tail 0.25` and
`benchmark_models --tail 0.25` hold out the last quarter of a recording.
Even so, held-out frames from the same route, light and day overstate
performance on new routes.
