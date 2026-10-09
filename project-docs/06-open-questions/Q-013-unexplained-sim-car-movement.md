# Q-013 · The sim car once moved ~21 m on its own

- **Opened:** 2026-10-06 · **Status:** Closed (not reproduced) · **Priority:** low

While parked during phase 2 tests, the sim car moved about 21 m. The cause
wasn't found (likely a leftover publisher from a test script). It didn't
recur once every run logged the start position. If it happens again, check
for stray `/cmd_vel`/`/cmd_ackermann` publishers first.
