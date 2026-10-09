# Glossary

| Term | Meaning |
| --- | --- |
| **Traversability** | Whether the cart may drive over a patch of ground |
| **Ground plane** | The road surface fitted as a plane per frame |
| **Height above ground** | Signed distance of a point from the ground plane |
| **`camera_ground`** | Frame on the road directly below the camera: X forward, Y left, Z up |
| **Point labels** | 0 unknown/masked, 1 ground, 2 obstacle, 3 drop, 4 overhead |
| **Semantic classes** | 1 road, 2 sidewalk, 3 terrain (grass, vegetation, dirt), 4 other |
| **Forbidden surface** | Sidewalk or terrain: flat but lethal |
| **Patch rule** | A small flat "other" region mostly surrounded by road is free (paint, paper, stains, manholes) |
| **Fusion** | Combining geometry labels and semantic classes per grid cell |
| **Zero-shot** | A pretrained model used without training on our data, its labels mapped to our classes |
| **Teacher** | Mask2Former Swin-L (Mapillary Vistas), used offline to auto-label |
| **Student** | A small model trained on auto-labels (SegFormer-B0/B2 or DINOv2) |
| **RGB-D student** | A student with height above ground as a fourth input channel |
| **Flat-road recall** | Share of flat road pixels (patches included) the model calls road |
| **Forbidden recall** | Share of sidewalk and terrain pixels the model catches |
| **IDD** | India Driving Dataset (human labels; needs a free account) |
| **Engine** | A TensorRT model built on the Orin from ONNX with `trtexec` |
| **MCAP** | ROS 2 bag file format |
