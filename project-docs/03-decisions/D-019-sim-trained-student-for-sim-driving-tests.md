# D-019 · Use the sim-trained RGB-D student for driving tests in the sim

- **Date:** 2026-10-08
- **Status:** Accepted (owner's direction)

For `cart_driver` tests in tesla_sim, perception runs the sim-trained
SegFormer-B0 RGB-D student plus depth
(`student:~/traversability_data/students/b0_rgbd_sim/best.pt`, the default in
`cart_driver`'s `sim.launch.py`). It isn't a real-world model.
