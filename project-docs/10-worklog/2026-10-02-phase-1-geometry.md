# 2026-10-02 · Phase 1: geometry baseline

**Who:** project owner, with Claude Code
**Goal:** replace the YOLO road model's failure on flat road patches.

## What was done
- Discussed depth-based approaches (ground plane, V-disparity, RGB-D
  segmentation, learned stereo); reviewed `road_segmentation` (bugs noted,
  not fixed).
- Owner: don't change `road_segmentation`; target Orin AGX; sidewalks and
  grass forbidden ([D-001](../03-decisions/D-001-new-package-leave-road-segmentation-alone.md), [D-006](../03-decisions/D-006-target-jetson-orin-agx.md), [D-007](../03-decisions/D-007-four-classes-sidewalk-and-grass-forbidden.md)).
- Built phase 1 (`20995d6`): geometry, grid, noise node, test scene, 9 tests.
- Set up on the Orin; synthetic-feed test; D435i launch, RViz, `snapshot`
  (`01c7342`, `da7ab47`).
- Created BITSAuto/traversability and pushed `main`.
- Discussed RTAB-Map ([D-003](../03-decisions/D-003-per-frame-gravity-constrained-plane-no-slam.md)) and model choices including SAM/DINO ([D-008](../03-decisions/D-008-semantic-segmentation-not-yolo-or-sam.md)).

## Results
[phase1-test-scene.md](../09-testing-and-results/phase1-test-scene.md).
