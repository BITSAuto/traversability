# Campus bag, 2026-10-01

- **What:** a 54.7 s drive around campus with the D435i, recorded with ROS 2
  (Jazzy) as MCAP; 16.8 GB; 68,406 messages; 1635 colour frames.
- **Topics used:** 1280×720 colour, depth aligned to colour, accelerometer,
  `/tf_static`; raw and lossless.
- **Scene:** campus road with grass verges, raised curbs, a paved walkway, a
  parked car, scooters, people, planters, buildings; evening light.
- **Problem:** the file was never closed: no MCAP index or footer, last record
  truncated. `ros2 bag` may refuse such files.
- **Repair (2026-10-07):** copy every complete record and append a proper
  ending; only the truncated final chunk was dropped. Result at
  `~/traversability_data/campus_bag_20261001/bag_0.mcap` (laptop).
- **Download note:** the browser download stalled at 1.79 GB; it was resumed
  from the partial file (verified byte-for-byte against the source first).
  The source folder link is in the team's Drive; the original and partial
  files in the owner's Downloads folder are now redundant.
- **Processing (Orin):** `ros2 bag play` → `ground_geometry` + `record_frames`
  every 0.25 s → **144 frames** → `autolabel`. Students trained on the first
  75 % (108 frames), evaluated on the last 25 % (36 frames).
- **Results:** [campus-results.md](../09-testing-and-results/campus-results.md).
