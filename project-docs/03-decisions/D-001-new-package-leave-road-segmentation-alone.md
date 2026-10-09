# D-001 · A new package; leave `road_segmentation` alone

- **Date:** 2026-10-02
- **Status:** Accepted (owner's instruction)

## Context
Reviewing `road_segmentation` found the costmap node used depth only to place
pixels, never to judge height, plus several bugs (grid rotated relative to
its frame, a depth-unit check that misfires on `inf`, unseen cells marked
occupied, a letterbox-shifted mask). Fixing them in place was proposed.

## Decision
The owner: "Don't change anything in road_segmentation. I don't think YOLO is
the best model for this anyway." Build a new package, `traversability`.

## Consequences
- `road_segmentation` stays as it is; its bugs are noted here only for
  reference ([legacy-road-segmentation.md](../04-knowledge/legacy-road-segmentation.md)).
