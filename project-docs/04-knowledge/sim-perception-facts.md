# Sim perception facts

**Verified** in tesla_sim (details in tesla_sim's book):
- Depth is perfect 32FC1 metres, `inf` beyond max range. Use
  `depth_noise_coeff: 0` and optionally the `depth_noise` node.
- Sensor stamps are wall-clock; `/clock` is sim time (about 0.55×).
- The start is inside an intersection whose visible surface is ~10 cm above
  its collision surface: spawned objects sink and a 12 cm visual step
  appears ~8 m ahead. The test scene runs ~20 m further on, on `road(5)`.
  Plain road segments' collision surfaces are ~2 cm below the visible one.
- Webots roads can't have holes, so drops can't be tested.
- With the camera at the cart's mount (2026-10-08), the bonnet hides the road
  out to about 2.7 m.
- `config/tesla_sim.yaml`'s comments still describe the pre-2026-10-08 mount
  (~1.24 m); the values worked in all `cart_driver` runs since, but haven't
  been re-derived ([Q-011](../06-open-questions/Q-011-sim-config-predates-the-new-mount.md)).
