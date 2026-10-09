# Data and labelling bugs

## M-06: First auto-labels on real data were wrong at range
- **Found:** 2026-10-07
- **Symptom:** distant road labelled as obstacles; grass verges as "other".
- **Root cause:** real D435i depth noise is about twice the assumed level
  (±30 cm at 8–12 m), so geometry overrode the teacher wrongly.
- **Fix:** trust geometry within 6 m only; widen thresholds with distance;
  let "raised" override only a teacher road label
  ([D-016](../03-decisions/D-016-distance-aware-auto-labels.md)).
- **Rule:** measure the real sensor's noise before trusting a model of it.

## M-07: The student inherited the teacher's grass error
- **Found:** 2026-10-06
- **Symptom:** the sim student calls the grass mat road.
- **Root cause:** 97 % of grass clutter in its training data was
  auto-labelled road by Mask2Former. Geometry can only correct towards road.
- **Status:** open ([Q-001](../06-open-questions/Q-001-models-call-flat-grass-road.md)).

## M-08: Every-n-th-frame validation overstates accuracy
- **Found:** 2026-10-07
- **Root cause:** neighbouring frames are near-duplicates.
- **Fix:** hold out the end of the recording (`--val-tail`/`--tail`,
  [D-017](../03-decisions/D-017-time-split-validation.md)).

## M-09: The campus bag was never closed
- **Found:** 2026-10-06
- **Symptom:** MCAP without index or footer, last record truncated;
  `ros2 bag` may refuse it.
- **Fix:** repaired copy ([D-015](../03-decisions/D-015-repair-the-unclosed-campus-bag.md)).
- **Rule:** stop `ros2 bag record` with Ctrl-C and wait for it to exit
  before copying or uploading.
