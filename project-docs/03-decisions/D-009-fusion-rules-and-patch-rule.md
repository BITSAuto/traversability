# D-009 · Fusion rules and the patch rule

- **Date:** 2026-10-06
- **Status:** Accepted

Per cell: geometry obstacle/drop → lethal; ground + road → free;
ground + sidewalk/terrain → lethal; ground + "other" → free only if the
connected region is ≤ 2 m² and ≥ 75 % of its border is road, else lethal;
ground outside the colour camera's view → unknown.

**Why geometry always wins:** a model calling a box "road" must not free it.
**Why the size cap:** a large unrecognised region shouldn't be freed just
because road surrounds it.
