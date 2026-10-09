# D-015 · Repair the unclosed campus bag rather than re-record

- **Date:** 2026-10-07
- **Status:** Accepted

The 2026-10-01 recording (54.7 s, 16.8 GB MCAP) was never closed: no index,
no footer, last record cut short. A repaired copy keeps every complete record
and writes a proper ending; only the final truncated chunk was dropped. ROS
reads all 68,406 messages. Lesson for recording: stop the recorder cleanly.
The download itself was resumed from a 1.79 GB partial file after checking it
matched the source byte for byte.
