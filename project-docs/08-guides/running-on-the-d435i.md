# Running on the D435i (Orin)

```bash
source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash
ros2 launch traversability d435i.launch.py                     # driver + geometry
ros2 launch traversability d435i.launch.py semantics:=true     # + SegFormer-B0 engine
ros2 launch traversability d435i.launch.py rviz:=true          # needs a display
ros2 run traversability snapshot                               # headless PNG: colour, labels, grid
```
- USB 3 port; on USB 2 add `fps:=15`.
- RGB-D models need `align:=true`.
- Use your own `ROS_DOMAIN_ID` if other stacks run on the Orin.
- First check: camera 0.5–1.5 m up, pointing slightly down; a newspaper or
  mat must stay free, a box or bag (> ~8 cm) lethal. No body mask yet, so
  feet or the cart's edge show as obstacles.
