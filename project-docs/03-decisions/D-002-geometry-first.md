# D-002 · Geometry first: depth ground plane as the safety layer

- **Date:** 2026-10-02
- **Status:** Accepted

## Context
Paint or a newspaper has essentially zero height. Geometrically it is part of
the ground, so "is this drivable ground?" replaces "does this look like
road?".

## Decision
Phase 1 is a depth-only baseline (no learning): fit the ground plane, label
by height, build the grid. Semantics come later, fused on top.

## Alternatives considered
- **Fix the appearance model only** (copy-paste augmentation, hole filling):
  still useful as training tricks, but hole filling is dangerous without
  geometry confirming the area is flat.
- **Stereo-image segmentation / learned stereo:** on the D435i, depth already
  comes from stereo matching; learned stereo (RAFT-Stereo etc.) only if the
  onboard depth becomes the bottleneck.

## Consequences
- Fixes the original failure without any model.
- Can't tell road from flat grass or a flush sidewalk (phase 2).
