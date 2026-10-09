# Frames and conventions

- **`camera_ground`**: on the road directly below the camera; X forward,
  Y left, Z up (normal of the fitted plane). Published per frame by
  `ground_geometry` as a TF from the depth sensor's frame.
- **Point labels** (`ground_points.label`): 0 unknown/masked, 1 ground,
  2 obstacle, 3 drop, 4 overhead (above `clearance_height`).
- **Semantic classes**: 1 road, 2 sidewalk, 3 terrain, 4 other (0 none).
- **Grid values**: 0 free, 100 lethal, −1 unknown. The grid's origin and
  extent are in `camera_ground`; `x_min = 0` means it starts at the camera.
- **Depth units**: 32FC1 metres (sim) or 16UC1 millimetres (D435i,
  `depth_scale` 0.001), decided by encoding, never by value range.
- Consumers that keep a map over time (cart_driver) must place each grid at
  the camera pose **at the frame's capture time**.
