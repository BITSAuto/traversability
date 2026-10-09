# Q-005 · Low obstacles at range under real noise

- **Opened:** 2026-10-02 · **Status:** Open · **Priority:** medium

With D435-like noise the height margin at 5–7 m is about 0.15 m; a 13 cm curb
there was detected in only ~11 of 90 cells. Ideas: per-cell height
statistics instead of per-point thresholds; temporal accumulation (now in
`cart_driver`'s map); a learned RGB-D model.
