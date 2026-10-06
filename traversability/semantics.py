"""Traversability semantic classes and label-set mappings (pure numpy).

Every model and dataset is reduced to the same four classes, chosen for what
the fusion needs to decide rather than for scene understanding:

  ROAD      drivable surface, including markings, crossings, manholes
  SIDEWALK  pedestrian surfaces and curbs              -> forbidden
  TERRAIN   grass, vegetation, soil, sand, water, ...  -> forbidden
  OTHER     everything else (objects, buildings, sky, unknown flat things)

On flat ground, OTHER is the interesting case: it is either a patch on the
road (paint, a newspaper) or something we have no business driving onto.
The fusion decides which by shape and surroundings (see fusion.py).
"""

import numpy as np

NONE = 0        # no semantic information (outside the image, not yet computed)
ROAD = 1
SIDEWALK = 2
TERRAIN = 3
OTHER = 4
IGNORE = 255    # training-label "don't care"

NAMES = {NONE: 'none', ROAD: 'road', SIDEWALK: 'sidewalk', TERRAIN: 'terrain', OTHER: 'other'}
NUM_CLASSES = 4                       # ROAD..OTHER; model output channel i is class i + 1
FORBIDDEN = (SIDEWALK, TERRAIN)

# BGR, for overlays.
COLORS = np.array([
    (0, 0, 0),          # none
    (128, 64, 128),     # road (Cityscapes purple)
    (232, 35, 244),     # sidewalk (magenta)
    (35, 142, 107),     # terrain (green)
    (0, 170, 255),      # other (orange)
], np.uint8)

# Label names (lower-cased) per source label set. Anything not listed maps to
# OTHER, except names in _IGNORED.
_ROAD = {
    # Cityscapes
    'road',
    # Mapillary Vistas
    'bike lane', 'crosswalk - plain', 'lane marking - crosswalk', 'lane marking - general',
    'manhole', 'catch basin', 'parking', 'service lane',
    # IDD
    'drivable fallback',
}
_SIDEWALK = {
    'sidewalk', 'curb', 'curb cut', 'pedestrian area',
}
_TERRAIN = {
    'vegetation', 'terrain', 'sand', 'snow', 'mountain', 'water', 'rail track',
    # IDD: unpaved/grass ground beside the road
    'non-drivable fallback',
}
_IGNORED = {
    'ego vehicle', 'car mount', 'unlabeled', 'rectification border', 'out of roi', 'license plate',
}


def map_name(name):
    n = name.strip().lower()
    if n in _IGNORED:
        return IGNORE
    if n in _ROAD:
        return ROAD
    if n in _SIDEWALK:
        return SIDEWALK
    if n in _TERRAIN:
        return TERRAIN
    return OTHER


def class_lut(names):
    """Lookup table: source label index -> traversability class."""
    return np.array([map_name(n) for n in names], np.uint8)


def aggregation_matrix(names):
    """(NUM_CLASSES, len(names)) 0/1 matrix summing source probabilities into
    our classes. Ignored source labels contribute to no class."""
    lut = class_lut(names)
    m = np.zeros((NUM_CLASSES, len(names)), np.float32)
    for src, dst in enumerate(lut):
        if dst != IGNORE:
            m[dst - 1, src] = 1.0
    return m


def colorize(classes):
    return COLORS[np.minimum(classes, len(COLORS) - 1)]
