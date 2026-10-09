# D-016 · Distance-aware auto-labels for real D435i depth

- **Date:** 2026-10-07
- **Status:** Accepted (`1134e58`)

Real depth noise was about twice the assumed level (road height spread ±4 cm
at 0–3 m, ±30 cm at 8–12 m). First auto-labels marked distant road as
obstacles and verges as "other". `autolabel` now trusts geometry only within
6 m, widens thresholds with distance (c = 0.01), and lets "raised" override
only a teacher road label.
