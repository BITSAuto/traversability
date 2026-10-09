# Viewing in RViz

- Fixed frame: `camera_ground`.
- `Map` display on `/traversability/grid`.
- `PointCloud2` on `/traversability/ground_points`, colour by `label`.
- `Image` on `/traversability/semantics_overlay`.
- `config/traversability.rviz` has this layout; `d435i.launch.py rviz:=true`
  opens it.
- Headless (SSH): `ros2 run traversability snapshot` instead.
