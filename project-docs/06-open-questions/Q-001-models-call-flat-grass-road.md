# Q-001 · Models call flat grass lying on the road "road"

- **Opened:** 2026-10-06 · **Status:** Open · **Priority:** high

In the sim test scene, a grass mat in the lane at 5.5 m is called road by
SegFormer-B2, Mask2Former and the sim student (B0 catches 80–89 %). Geometry
can't help: it's flat. The student inherits the teacher's error (97 % of
grass clutter auto-labelled road). **Likely fix:** human labels (IDD,
hand-corrected campus frames) and more real data. Check how often this
happens on real verges once there is more data.
