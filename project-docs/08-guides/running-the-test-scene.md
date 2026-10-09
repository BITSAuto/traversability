# Running the test scene

The start pose is inside an intersection where objects sink; drive about
20 m first:
```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 3.0}}"   # ~7 s, then Ctrl-C
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
ros2 run traversability spawn_test_scene
ros2 run traversability check_test_scene --ros-args -p frames:=20                 # geometry only
ros2 run traversability check_test_scene --ros-args -p frames:=10 -p mode:=fused  # with semantics
ros2 run traversability spawn_test_scene --ros-args -p remove_only:=true          # remove
```
(Since 2026-10-08 the sim coasts at 0.4 m/s² when the command stops, so it
rolls ~1 m further than before.)

The scene: four flat objects that must be free (paint line, newspaper, oil
stain, grass patch) and four obstacles that must be lethal (0.15 m brick,
3 m × 0.15 m curb, 0.5 m box, 1 m barrel), 3.5–9 m ahead. In `fused` mode
the grass must be lethal. The check also counts lethal cells on open road.
