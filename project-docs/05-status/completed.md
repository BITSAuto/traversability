# Completed

## 2026-10-09 · Project docs
This book ([D-020](../03-decisions/D-020-project-docs.md)).

## 2026-10-08 · RGB-D height at reduced resolution — [PR #2](https://github.com/BITSAuto/traversability/pull/2) (`4f90f5b`, merged `f5fed65`)
Semantics latency in the sim 0.67 → 0.21 s ([D-018](../03-decisions/D-018-rgbd-height-at-reduced-resolution.md)).

## 2026-10-07 · Real campus data — in [PR #1](https://github.com/BITSAuto/traversability/pull/1) (`1134e58`, `c8ed526`)
Bag repaired and processed; distance-aware auto-labels; time-split
validation; campus students trained and benchmarked; full pipeline run on
the Orin against the bag ([D-015](../03-decisions/D-015-repair-the-unclosed-campus-bag.md)–[D-017](../03-decisions/D-017-time-split-validation.md)).

## 2026-10-06 · Phases 2 and 3 — in [PR #1](https://github.com/BITSAuto/traversability/pull/1) (`0fdcfb0`), merged `8165bca` on 2026-10-07
`semantic_seg` with `hf:`/`student:`/`trt:` backends, fusion, recording,
auto-labelling, training, benchmarking, export; validated in the sim and on
the Orin ([D-009](../03-decisions/D-009-fusion-rules-and-patch-rule.md)–[D-014](../03-decisions/D-014-default-model-zero-shot-segformer-b0.md)).

## 2026-10-02 · Phase 1 and the Orin — `20995d6`, `01c7342`, `da7ab47`
Geometry baseline, test scene and checker, depth noise node, D435i launch
and config, RViz layout, `snapshot`; set up and tested on the Orin; repo
created as BITSAuto/traversability ([D-001](../03-decisions/D-001-new-package-leave-road-segmentation-alone.md)–[D-008](../03-decisions/D-008-semantic-segmentation-not-yolo-or-sam.md)).
