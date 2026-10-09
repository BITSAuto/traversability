# traversability · Project docs

The shared engineering record for **traversability**, the BITSAuto cart's
perception: depth ground-plane geometry fused with semantic segmentation into
an occupancy grid, plus the pipeline that trains and deploys our own models.
The usage summary is the top-level [README](../README.md); this book holds
the history, reasoning and status.

## Start here

| If you are... | Read |
| --- | --- |
| new to the project | [01-overview](01-overview/README.md), then [05-status](05-status/README.md) |
| changing perception code | [02-architecture](02-architecture/README.md), the [decisions](03-decisions/README.md) and [bugs-and-lessons](07-bugs-and-lessons/README.md) |
| collecting data or training | [08-guides](08-guides/README.md) and [09-testing-and-results](09-testing-and-results/README.md) |
| an AI agent | [AGENTS.md](../AGENTS.md), then this page |

## Status at a glance (2026-10-09)

Phases 1–3 merged: geometry baseline, semantic fusion, training pipeline,
TensorRT on the Orin. Zero-shot SegFormer-B0 is the default. One real campus
drive processed; a campus-trained student is promising but the data is tiny
and labels are unchecked. Main needs: more varied campus recordings, a
hand-checked test set, IDD. Never run live on the cart-mounted camera.

## Contents

1. **[Overview](01-overview/README.md)** —
   [project brief](01-overview/project-brief.md) ·
   [system map](01-overview/system-map.md) ·
   [hardware and environment](01-overview/hardware-and-environment.md) ·
   [glossary](01-overview/glossary.md)
2. **[Architecture](02-architecture/README.md)** —
   [components](02-architecture/components.md) ·
   [interfaces](02-architecture/interfaces.md) ·
   [frames and conventions](02-architecture/frames-and-conventions.md) ·
   [geometry pipeline](02-architecture/geometry-pipeline.md) ·
   [semantics and fusion](02-architecture/semantics-and-fusion.md) ·
   [learning pipeline](02-architecture/learning-pipeline.md) ·
   [deployment on the Orin](02-architecture/deployment-on-orin.md)
3. **[Decisions](03-decisions/README.md)** — D-001 to D-020
4. **[Knowledge](04-knowledge/README.md)** —
   [real D435i data](04-knowledge/real-d435i-data.md) ·
   [campus bag](04-knowledge/campus-bag-2026-10-01.md) ·
   [models and datasets](04-knowledge/models-and-datasets.md) ·
   [Orin environment](04-knowledge/orin-environment.md) ·
   [laptop Python environment](04-knowledge/laptop-python-environment.md) ·
   [sim perception facts](04-knowledge/sim-perception-facts.md) ·
   [legacy road_segmentation](04-knowledge/legacy-road-segmentation.md)
5. **[Status](05-status/README.md)** —
   [completed](05-status/completed.md) ·
   [in progress](05-status/in-progress.md) ·
   [roadmap](05-status/roadmap.md)
6. **[Open questions](06-open-questions/README.md)** — Q-001 to Q-013
7. **[Bugs and lessons](07-bugs-and-lessons/README.md)** —
   [pipeline](07-bugs-and-lessons/pipeline-bugs.md) ·
   [data and labelling](07-bugs-and-lessons/data-and-labelling-bugs.md) ·
   [integration](07-bugs-and-lessons/integration-bugs.md) ·
   [environment and process](07-bugs-and-lessons/environment-and-process-bugs.md)
8. **[Guides](08-guides/README.md)** —
   [setup](08-guides/setup-and-build.md) ·
   [sim](08-guides/running-in-the-sim.md) ·
   [test scene](08-guides/running-the-test-scene.md) ·
   [D435i](08-guides/running-on-the-d435i.md) ·
   [recording and replaying](08-guides/recording-and-replaying.md) ·
   [training](08-guides/training-a-model.md) ·
   [TensorRT](08-guides/deploying-a-tensorrt-engine.md) ·
   [RViz](08-guides/viewing-in-rviz.md)
9. **[Testing and results](09-testing-and-results/README.md)** —
   [unit tests](09-testing-and-results/unit-tests.md) ·
   [phase 1 scene](09-testing-and-results/phase1-test-scene.md) ·
   [phase 2 scene](09-testing-and-results/phase2-fused-test-scene.md) ·
   [sim student](09-testing-and-results/sim-student.md) ·
   [campus](09-testing-and-results/campus-results.md) ·
   [Orin latency](09-testing-and-results/orin-latency.md) ·
   [sim latency under load](09-testing-and-results/sim-latency-under-load.md)
10. **[Worklog](10-worklog/README.md)** — one page per work session

## How to keep this book current

This book is only useful if it is never stale. **Every piece of work updates
it in the same branch or PR** as the work itself: code, experiments,
debugging, field tests, measurements, and decisions made in a meeting or a
chat. A PR without a docs update is incomplete (the PR template has the
checklist).

| When you... | Update |
| --- | --- |
| do any work at all | add a page to `10-worklog/` (copy the template in its README) and adjust `05-status/` |
| decide something (including "we won't do X") | add `03-decisions/D-NNN-slug.md` and a row in its index. To reverse a decision, add a new one that supersedes it and mark the old one *Superseded by D-NNN*; don't delete it |
| verify a fact (measurement, datasheet, reading source code, a live test) | add it to the right page in `04-knowledge/` with a confidence tag and *how* it was checked |
| hit something unknown that matters | add `06-open-questions/Q-NNN-slug.md` and a row in its index |
| answer an open question | set its status to *Resolved*, say what resolved it and link to where the answer now lives; keep the page |
| find a bug (yours or anyone's) | record it in `07-bugs-and-lessons/`: symptom, root cause, fix, and the rule that would have prevented it |
| change how to build, run, deploy or calibrate | update `08-guides/` |
| get a new test or scenario result | update `09-testing-and-results/` |
| change architecture, topics, parameters or conventions | update `02-architecture/` |

**Writing rules**
- **Append, don't rewrite history.** If something written here turns out to be
  wrong, add a dated *Correction (YYYY-MM-DD):* under it. Knowing that
  something was believed and then disproved is useful.
- **Say how you know.** Confidence tags: **Verified** (checked directly
  against source code, a live system or a measurement; say which),
  **Documented** (from a datasheet or other docs, not re-checked here),
  **Assumed** (a guess, placeholder or inference; must also appear in open
  questions if it matters). Never let repetition upgrade an assumption.
- **Date everything** (YYYY-MM-DD) and link PRs, commits and issues.
- **One topic per page.** Add pages rather than growing one page forever.
  Each chapter's `README.md` lists its pages; keep that list in sync.
- **Link, don't duplicate.** Facts about another repo's component belong in
  that repo's book; link to it.
- **No secrets or personal details.** No passwords, tokens, private IPs,
  personal machine configs or e-mail addresses. Three of our repos are
  public.
- **Write for someone who wasn't there.** Spell out the why, not just the
  what.
