# The old YOLO costmap (`road_segmentation`), for reference

**Verified** by reading the code on 2026-10-02. Not fixed, by the owner's
instruction ([D-001](../03-decisions/D-001-new-package-leave-road-segmentation-alone.md)).

- `mask_to_costmap_node` uses depth only to place pixels on the grid, never to
  judge height, so anything the model doesn't call road becomes an obstacle.
- The grid is rotated relative to its frame (lateral distance filled along
  columns, forward along rows; points should map body x = z, y = −x).
- The depth-unit check (`max() > 100` ⇒ millimetres) misfires on Webots'
  `inf` beyond max range, scaling every depth by 0.001. Decide by encoding.
- Unseen cells are marked occupied (100), not unknown (−1).
- Without `retina_masks=True`, ultralytics masks include letterbox padding and
  are shifted when stretched to 1280×720.
- Logs every mask at info level; `confidence` defaults to 0.85;
  `show_display` defaults to true.
- YOLO11-seg is instance segmentation, the wrong formulation for road
  ([D-008](../03-decisions/D-008-semantic-segmentation-not-yolo-or-sam.md)).
