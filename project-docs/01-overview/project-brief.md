# Project brief

## The problem
The team's earlier road model (`road_segmentation`, YOLO instance
segmentation) fails when something flat lies on the road: paint, a
newspaper, an oil stain. It doesn't look like road, so the model marks it
non-road, and the costmap turns it into an obstacle, although the cart could
drive straight over it.

## The approach
Judge "can the cart drive here?" from **geometry first**, and use appearance
only for what geometry can't tell:

1. **Depth geometry (phase 1).** Fit the road as a plane in each depth frame
   (RANSAC, constrained by the IMU's gravity direction) and label every point
   by its height above it. Flat things are ground whatever they look like;
   anything raised (> ~8 cm) or dropped is an obstacle.
2. **Semantics (phase 2).** Flat grass or a flush sidewalk is geometrically
   identical to road, and both are **forbidden**. A segmentation model labels
   each pixel road / sidewalk / terrain / other, and fusion rules combine the
   two: obstacles always lethal, road free, sidewalk and terrain lethal, and a
   small flat "other" patch surrounded by road free.
3. **Our own model (phase 3).** Record campus data, auto-label it with a big
   teacher model corrected by geometry, train a small student (optionally
   with height above ground as a fourth input), and deploy it with TensorRT
   on the Orin.

Output: a local `nav_msgs/OccupancyGrid` on `/traversability/grid` in the
`camera_ground` frame (0 free, 100 lethal, −1 unknown), consumed by
`cart_driver`.

## Status (2026-10-09)
All three phases are built and merged. Phase 1 passes the sim test scene with
perfect and noisy depth. Fusion works with every model tried. Real campus
data (one 55 s drive) has been processed; a campus-trained student beats
zero-shot models on held-out frames but the dataset is tiny. **Zero-shot
SegFormer-B0 is the default** on the Orin. The weak point is a model calling
forbidden flat ground "road" (the sim grass mat); only better labels fix
that. Never run live on the cart-mounted camera yet.

## Scope and non-goals
- Local, per-frame perception. Memory over time is `cart_driver`'s job (its
  local map), not this package's.
- No SLAM, no odometry dependency.
- `road_segmentation` is not modified ([D-001](../03-decisions/D-001-new-package-leave-road-segmentation-alone.md)).
