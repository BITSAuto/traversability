# Working in this repository

This repo keeps a shared engineering record in [`project-docs/`](project-docs/README.md).
It is the team's common context: anyone (human or AI agent) should be able to
find what exists, why it is that way, what is being worked on and what is
still unknown, from that folder alone.

**Before starting work:** read `project-docs/README.md`, then the chapters it
points you to for the area you are touching (at least the relevant decisions,
open questions and bugs-and-lessons pages).

**Every piece of work updates `project-docs/` in the same branch or PR.**
That includes code changes, experiments, debugging sessions, measurements and
decisions made in conversation. The minimum is a worklog page plus the status
pages; the full checklist is in
[`project-docs/README.md`](project-docs/README.md#how-to-keep-this-book-current).

Other rules:
- Work on a branch and open a PR; never force-push or bypass hooks.
- Respect the cross-repo rules in `project-docs/01-overview/system-map.md`
  (emergency-only braking, + = right steering, one vehicle per ROS domain).
- No secrets, passwords, tokens or personal machine details in this repo.
