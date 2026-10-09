# Real D435i data

### Depth noise is about twice the first estimate
**Verified** on the 2026-10-01 campus bag: the height spread of
teacher-labelled road grows from **±4 cm at 0–3 m to ±30 cm at 8–12 m**.
The sim noise model used σ_z = c·z² with c ≈ 0.005 (D435 rule of thumb).
Consequences: auto-labels trust geometry only within 6 m (c = 0.01 there);
low obstacles beyond ~5 m are detected only sparsely.

### Camera mount on the cart
**Verified** from the plane fit on the bag: camera **1.51–1.53 m** above the
road, pitched about **9°** down, centred.

### What the full pipeline does on real campus road
**Verified** on bag replay on the Orin (2026-10-07): the road ahead comes out
free with no false obstacles in the lane; curbs, parked scooters, people and
planters come out lethal; paved parking areas and footpaths are flat (free by
geometry alone) and become lethal only with a semantic model calling them
sidewalk.

### Outdoor stereo caveats
**Documented** (RealSense guidance): direct sunlight washes out the IR
projector (passive stereo then; fine on textured asphalt, holes on uniform
surfaces); water, glass and shiny surfaces give bad depth.

### Synthetic test before the camera was available
**Verified** (2026-10-02, Orin): on a fake D435i feed with realistic noise
(camera 1.0 m up, 8° down, a thin patch and a box), the pipeline recovered
height 1.000 m and tilt 8.0°, kept the patch free and placed the box
correctly.
