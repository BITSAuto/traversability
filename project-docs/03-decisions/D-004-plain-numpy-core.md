# D-004 · Plain numpy core, unit-tested, no Open3D/PCL

- **Date:** 2026-10-02
- **Status:** Accepted

Back-projection, vectorised RANSAC, the plane tracker, labelling, the grid
and fusion are plain numpy/cv2 in modules with no ROS dependency. They run
unchanged on the Orin, can be profiled outside ROS, and have unit tests.
