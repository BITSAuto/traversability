# Running in the sim

Start tesla_sim first (its book, `08-guides/running-the-sim.md`), then in a
second terminal on the same `ROS_DOMAIN_ID`, inside the distrobox:
```bash
ros2 launch traversability traversability.launch.py                       # perfect depth, geometry only
ros2 launch traversability traversability.launch.py noise:=true           # D435-like noise
ros2 launch traversability traversability.launch.py semantics:=true       # + SegFormer-B2 (default)
ros2 launch traversability traversability.launch.py semantics:=true model:=student:$HOME/traversability_data/students/b0_rgbd_sim/best.pt
```
- Model loading takes a minute or two before `/traversability/grid` appears.
- RGB-D students need the registered depth (published by tesla_sim).
- `cart_driver`'s `sim.launch.py` includes this launch with the sim student.
