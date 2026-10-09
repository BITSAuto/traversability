# Roadmap

| # | Item | Why | Needs |
| --- | --- | --- | --- |
| 1 | Record 20–30 min of campus driving: different routes, daylight, dusk, night, wet roads, camera at its final mount | The single biggest improvement | someone on campus |
| 2 | Hand-correct 50–100 frames from routes not used for training (e.g. CVAT) | True accuracy instead of agreement with the teacher | labelling time |
| 3 | Download IDD (level3Ids) and train with `--idd` | Human labels for sidewalks and verges | owner creates the account |
| 4 | Retrain the campus student; compare with zero-shot B0 on the hand-checked set; switch the Orin default if it wins | Better forbidden-surface recall | 1–3 |
| 5 | Mount config for the real cart: `self_mask`, `camera_height_min`, re-check `fit_min_range` | Live use on the cart | fixed mount |
| 6 | Per-cell height statistics for low obstacles at range | Curbs at 5–7 m under noise | — |
| 7 | Compare DINOv2 students | May generalise better with few labels | data |
| 8 | Shared storage for datasets and models | They live on one laptop | team decision ([Q-010](../06-open-questions/Q-010-shared-storage-for-data-and-models.md)) |
