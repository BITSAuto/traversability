"""Training data: recorded frame folders, IDD, and augmentation.

All datasets yield (rgb uint8 HxWx3 RGB, height float32 HxW metres or NaN,
labels uint8 HxW in traversability classes with 255 = ignore).
"""

import glob
import json
import os

import cv2
import numpy as np

from traversability import geometry, semantics

# IDD level3Ids (what IDD's createLabels.py writes as *_labellevel3Ids.png),
# named after the AutoNUE toolkit's helpers/anue_labels.py: the name of the
# first label carrying each level3Id.
IDD_LEVEL3_NAMES = [
    'road', 'drivable fallback', 'sidewalk', 'non-drivable fallback', 'person', 'rider',
    'motorcycle', 'bicycle', 'autorickshaw', 'car', 'truck', 'bus', 'vehicle fallback',
    'curb', 'wall', 'fence', 'guard rail', 'billboard', 'traffic sign', 'traffic light',
    'pole', 'obs-str-bar-fallback', 'building', 'bridge', 'vegetation', 'sky',
]


def height_image(depth_m, K, R, t):
    """Height above ground for every pixel of a depth image registered to the
    colour camera, given the ground frame's pose in that camera (p = R g + t)."""
    fx, fy, cx, cy = K[0], K[4], K[2], K[5]
    points = geometry.deproject(depth_m, fx, fy, cx, cy, min_range=0.1)
    return (points - np.asarray(t)) @ np.asarray(R)[:, 2]


class FrameFolder:
    """Frames written by record_frames, optionally auto-labelled (labels/)."""

    def __init__(self, root, require_labels=True):
        self.root = root
        names = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(root, 'meta')))
        if require_labels:
            names = [n for n in names if os.path.exists(os.path.join(root, 'labels', n + '.png'))]
        self.names = names

    def __len__(self):
        return len(self.names)

    def rgb(self, i):
        return cv2.cvtColor(cv2.imread(os.path.join(self.root, 'rgb', self.names[i] + '.jpg')), cv2.COLOR_BGR2RGB)

    def meta(self, i):
        with open(os.path.join(self.root, 'meta', self.names[i] + '.json')) as f:
            return json.load(f)

    def depth(self, i):
        d = cv2.imread(os.path.join(self.root, 'depth', self.names[i] + '.png'), cv2.IMREAD_UNCHANGED)
        d = d.astype(np.float32) / 1000.0
        d[d <= 0] = np.nan
        return d

    def height(self, i):
        m = self.meta(i)
        return height_image(self.depth(i), m['K'], m['R'], m['t'])

    def labels(self, i):
        return cv2.imread(os.path.join(self.root, 'labels', self.names[i] + '.png'), cv2.IMREAD_UNCHANGED)

    def __getitem__(self, i):
        return self.rgb(i), self.height(i), self.labels(i)


class IDD:
    """IDD Segmentation (https://idd.insaan.iiit.ac.in/), after running the
    toolkit's createLabels.py with ``--id-type level3Ids``. No depth, so the
    height channel is all NaN (handled by height dropout in training)."""

    def __init__(self, root, split='train'):
        self.images = sorted(glob.glob(os.path.join(root, 'leftImg8bit', split, '*', '*_leftImg8bit.png')))
        if not self.images:
            raise FileNotFoundError(f'no IDD images under {root}/leftImg8bit/{split}')
        self.lut = np.full(256, semantics.IGNORE, np.uint8)
        self.lut[:len(IDD_LEVEL3_NAMES)] = semantics.class_lut(IDD_LEVEL3_NAMES)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, i):
        path = self.images[i]
        label_path = (path.replace('leftImg8bit', 'gtFine', 1)
                      .replace('_leftImg8bit.png', '_gtFine_labellevel3Ids.png'))
        rgb = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
        labels = self.lut[cv2.imread(label_path, cv2.IMREAD_UNCHANGED)]
        return rgb, np.full(rgb.shape[:2], np.nan, np.float32), labels


# ------------------------------------------------------------- augmentation
def _clutter_texture(rng, h, w):
    """A random flat-object texture: paper, paint, stain or tarmac patch."""
    kind = rng.integers(4)
    if kind == 0:       # newspaper-ish: light background, dark text lines
        tex = np.full((h, w, 3), rng.integers(190, 240), np.uint8)
        for y in range(int(rng.integers(2, 6)), h, int(rng.integers(3, 7))):
            x1 = int(w * rng.uniform(0.4, 0.95))
            cv2.line(tex, (int(w * 0.05), y), (x1, y), tuple(int(c) for c in rng.integers(30, 90, 3)), 1)
    elif kind == 1:     # paint: saturated flat colour
        tex = np.empty((h, w, 3), np.uint8)
        tex[:] = rng.choice([(240, 240, 240), (240, 210, 40), (200, 40, 40), (40, 90, 200)])
    elif kind == 2:     # stain: dark, soft-edged
        tex = np.full((h, w, 3), rng.integers(5, 40), np.uint8)
    else:               # patched tarmac / cardboard: mid tone noise
        base = rng.integers(60, 170, 3)
        tex = (base[None, None] + rng.normal(0, 12, (h, w, 3))).clip(0, 255).astype(np.uint8)
    return tex


def paste_clutter(rgb, labels, rng, max_items=3):
    """Paste flat clutter onto road pixels, keeping their label ROAD.

    Teaches the model that paint, paper and stains on the road are road --
    the failure that started this project. Shapes are random quadrilaterals
    or ellipses placed where the label is already ROAD."""
    road_v, road_u = np.nonzero(labels == semantics.ROAD)
    if len(road_v) < 500:
        return rgb
    rgb = rgb.copy()
    h, w = labels.shape
    for _ in range(int(rng.integers(1, max_items + 1))):
        i = rng.integers(len(road_v))
        cy, cx = road_v[i], road_u[i]
        # Smaller near the horizon (higher in the image), larger near the camera.
        scale = 0.03 + 0.15 * cy / h
        ph, pw = max(4, int(h * scale * rng.uniform(0.3, 1.0))), max(4, int(w * scale * rng.uniform(0.5, 1.5)))
        mask = np.zeros((h, w), np.uint8)
        if rng.random() < 0.5:
            cv2.ellipse(mask, (int(cx), int(cy)), (pw // 2, ph // 2), float(rng.uniform(0, 180)), 0, 360, 1, -1)
        else:
            pts = np.array([[cx - pw / 2, cy - ph / 2], [cx + pw / 2, cy - ph / 2],
                            [cx + pw / 2, cy + ph / 2], [cx - pw / 2, cy + ph / 2]])
            pts += rng.normal(0, max(pw, ph) * 0.15, pts.shape)
            cv2.fillConvexPoly(mask, pts.astype(np.int32), 1)
        mask = mask.astype(bool) & (labels == semantics.ROAD)
        if not mask.any():
            continue
        tex = _clutter_texture(rng, h, w)
        alpha = rng.uniform(0.75, 1.0)
        rgb[mask] = (alpha * tex[mask] + (1 - alpha) * rgb[mask]).astype(np.uint8)
    return rgb


def augment(rgb, height, labels, size, rng, clutter=0.5, height_dropout=0.2):
    """Random scale/crop to ``size`` (w, h), flip, colour jitter, clutter
    paste and height dropout. Returns (rgb, height, labels) at ``size``."""
    tw, th = size
    s = rng.uniform(0.6, 1.4) * max(tw / rgb.shape[1], th / rgb.shape[0])
    nw, nh = max(tw, int(rgb.shape[1] * s)), max(th, int(rgb.shape[0] * s))
    rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    height = cv2.resize(height, (nw, nh), interpolation=cv2.INTER_NEAREST)
    labels = cv2.resize(labels, (nw, nh), interpolation=cv2.INTER_NEAREST)
    x0, y0 = rng.integers(0, nw - tw + 1), rng.integers(0, nh - th + 1)
    rgb, height, labels = (a[y0:y0 + th, x0:x0 + tw] for a in (rgb, height, labels))
    if rng.random() < 0.5:
        rgb, height, labels = rgb[:, ::-1], height[:, ::-1], labels[:, ::-1]
    if rng.random() < clutter:
        rgb = paste_clutter(np.ascontiguousarray(rgb), labels, rng)
    # Colour jitter: brightness, contrast, saturation.
    f = rgb.astype(np.float32)
    f = (f - f.mean()) * rng.uniform(0.75, 1.25) + f.mean() * rng.uniform(0.75, 1.25)
    grey = f.mean(axis=-1, keepdims=True)
    f = grey + (f - grey) * rng.uniform(0.7, 1.3)
    rgb = f.clip(0, 255).astype(np.uint8)
    if rng.random() < height_dropout:
        height = np.full_like(height, np.nan)
    return np.ascontiguousarray(rgb), np.ascontiguousarray(height), np.ascontiguousarray(labels)
