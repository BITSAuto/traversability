# Unit tests

```bash
python3 -m pytest test
```

| File | Tests | Covers |
| --- | --- | --- |
| `test/test_geometry.py` | 10 | plane fit recovers height and tilt; rejects planes outside the constraints; flat patch = ground, box = obstacle; ground-frame axes; thresholds and noise scaling; tracker smoothing and jump rejection; rasterisation; quaternion round trip; gap filling; `height_above` matches the full transform |
| `test/test_fusion.py` | 10 | small "other" patch on road is free; large or unenclosed "other" stays lethal; forbidden surfaces lethal and obstacles win; patch next to an obstacle still free; ground without semantics; ties go to forbidden; semantic projection; gap filling keeps classes; label mappings |
| `test/test_learning.py` | 8 | auto-label rules (flat patch → road, raised/unenclosed stays other, obstacle called road → other, low confidence ignored, raised terrain keeps its label, far noise ignored); IDD level3 mapping; height image; augmentation keeps labels; student forward shapes (torch) |

28 pass on the laptop (2026-10-08, PR #2); on the Orin the torch test is
skipped.
