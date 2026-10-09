# Orin environment

**Verified** 2026-10-02 to 2026-10-07:
- Ubuntu 24.04, ROS 2 Jazzy, `realsense2_camera`, `cv_bridge` and numpy were
  already installed; nothing had to be added for phase 1.
- TensorRT 10.16; `trtexec` at `/usr/src/tensorrt/bin/trtexec`. **No torch**,
  so the torch unit test is skipped there.
- Engines live in `~/traversability_models/`.
- Under `ros2 launch`, Ctrl-C makes Jazzy print "process has died, exit code
  -2" for the Python nodes; they actually shut down cleanly. Quietened in
  `da7ab47`.
- Other stacks may be running on the Orin (e.g. on domain 0, and a
  `kratos_cameras` service that scans `/dev/video*` and only streams on
  request); test on a separate `ROS_DOMAIN_ID`.
- The Orin's copy of this repo tracks the same remote; it may not have GitHub
  push credentials.
