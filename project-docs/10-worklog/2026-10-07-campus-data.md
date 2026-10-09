# 2026-10-07 · First real campus data, PR #1

**Who:** project owner, with Claude Code
**Branch / PR:** `feat/semantics-and-training`, [PR #1](https://github.com/BITSAuto/traversability/pull/1) (merged `8165bca` by the owner after GitHub 500s)

## What was done
- Repaired and processed the 2026-10-01 bag on the Orin (144 frames).
- Measured real depth noise (≈2× assumed); made auto-labels distance-aware;
  time-split validation (`1134e58`).
- Trained campus students; ran the full pipeline on the Orin against the bag.
- Explained the model choice and the fusion to the owner with figures.

## Results
[campus-results.md](../09-testing-and-results/campus-results.md).

## Decisions
D-014 to D-017.
