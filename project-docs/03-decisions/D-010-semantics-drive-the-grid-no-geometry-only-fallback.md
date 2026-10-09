# D-010 · Semantic frames drive the grid; never fall back to geometry-only

- **Date:** 2026-10-06
- **Status:** Accepted

## Context
Semantics arrive about 0.35 s (phase 2 on the laptop) after the camera
frame. Pairing each new depth cloud with the latest semantics mismatched
them.

## Decision
- Each semantic frame is paired with the buffered depth cloud whose stamp is
  closest (within `semantic_max_age`).
- If semantics stop for over 1 s, publish obstacles with ground **unknown**.

## Why
Geometry-only output would mark grass and sidewalks free; unknown is safe.
