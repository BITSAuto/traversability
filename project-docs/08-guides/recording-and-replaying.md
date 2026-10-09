# Recording and replaying

## Record training frames directly
```bash
ros2 launch traversability d435i.launch.py align:=true record_dir:=$HOME/traversability_data/campus_N   # real camera
ros2 run traversability record_frames --ros-args -p out_dir:=...                                       # sim, alongside the pipeline
```
Frames every 0.5 s (colour, registered depth, ground plane).

## Record a bag
Record colour, aligned depth, the accelerometer and `/tf_static`. **Stop the
recorder cleanly** (Ctrl-C and wait), or the MCAP is left without its index
and footer.

## Replay a bag through the pipeline (Orin; bags from Jazzy)
```bash
ros2 launch traversability d435i.launch.py camera:=false semantics:=true   # pipeline without the driver
ros2 bag play <bag>
ros2 run traversability record_frames --ros-args -p out_dir:=... -p min_interval:=0.25
```

## Repairing an unclosed MCAP
Copy every complete record into a new file and append a proper summary and
footer, dropping the truncated final record. The 2026-10-07 repair was a
one-off script that wasn't kept. Check message counts against the
recording's metadata afterwards (`ros2 bag info`).
