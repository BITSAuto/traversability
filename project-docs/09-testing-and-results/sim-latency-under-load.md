# Semantics latency in the sim under load (2026-10-08)

With tesla_sim, perception (sim RGB-D student) and `cart_driver` all on the
laptop:

| Version | Height image | Semantics latency |
| --- | --- | --- |
| before PR #2 | full resolution, full transform (~100 ms/frame) | 0.67 s (mostly unpairable) |
| after PR #2 | half resolution, `height_above` only | **0.21 s**, ~3× the rate; fused grid works from the new camera mount |
