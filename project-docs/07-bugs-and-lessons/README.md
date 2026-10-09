# 07 · Bugs and lessons

| Page | Bugs |
| --- | --- |
| [pipeline-bugs.md](pipeline-bugs.md) | M-01 semantics paired with the wrong cloud · M-02 duplicate semantic frames · M-03 geometry-only fallback would free grass · M-04 RealSense launch arguments not scoped · M-05 noisy Jazzy shutdown |
| [data-and-labelling-bugs.md](data-and-labelling-bugs.md) | M-06 auto-labels wrong on real depth · M-07 student inherits teacher errors · M-08 every-n-th validation flatters · M-09 unclosed bag file |
| [integration-bugs.md](integration-bugs.md) | M-10 RGB-D height too slow · M-11 `params` launch argument hijacked by an including launch |
| [environment-and-process-bugs.md](environment-and-process-bugs.md) | M-12 pip resolver bug · M-13 numpy 2 breaks `cv_bridge` · M-14 test scripts left nodes running · M-15 objects sink in the sim · M-16 GitHub 500 on merge |

## Lessons
- Time-align everything that arrives with different latency; pair by stamp.
- When an input disappears, fall back to *unknown*, never to a less safe
  interpretation.
- Measure the real sensor before trusting a noise model.
- A model trained on auto-labels inherits its teacher's blind spots.
- Launch arguments are global: never reuse a name an included launch uses.
