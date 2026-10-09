# Environment and process bugs

## M-12: pip 22.0.2's resolver bug
Ubuntu 22.04's pip failed to resolve the `transformers` install; upgrading
pip in the user site (25.3) fixed it.

## M-13: numpy 2 breaks `cv_bridge` on Humble
Keep `numpy==1.26.4` in the distrobox.

## M-14: Test scripts left nodes running that ignored Ctrl-C
Background jobs started from non-interactive scripts ignore SIGINT; nodes
survived and kept publishing. All were stopped by PID. Start launches through
a wrapper that restores SIGINT, and check for leftovers after test runs.

## M-15: Objects sink near the sim's start
Spawned objects sank into the start intersection (surface 10 cm above
collision). The test scene runs ~20 m further on (tesla_sim's book, Q-010).

## M-16: GitHub returned HTTP 500 for every write to `main`
On 2026-10-07 merging PR #1 failed through `gh`, the REST API and a direct
push, though the repo had no protection rules. The owner merged it from the
web UI later; the local merge commit was dropped so nothing diverged.
