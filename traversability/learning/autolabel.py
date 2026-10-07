"""Auto-label recorded frames: a strong teacher model, corrected by geometry.

  ros2 run traversability autolabel <frames_dir> [--teacher hf:...] [--viz]

For each frame from record_frames, the teacher (default Mask2Former Swin-L,
Mapillary Vistas -- slow, but the most fine-grained label set) gives
per-pixel classes, then depth geometry fixes what appearance gets wrong:

  * Teacher "road" that is clearly above the ground is OTHER (e.g. a box
    the teacher calls road). Geometry is only trusted within --max-range,
    with thresholds that widen with distance to follow stereo noise.
  * Small flat OTHER regions surrounded by flat ROAD become ROAD: these are
    the newspapers and paint marks the original model failed on, and
    labelling them road is what teaches the student to ignore them.
  * Teacher pixels below ``--min-confidence`` are ignored (255).

Writes <frames_dir>/labels/<n>.png (uint8 classes, 255 = ignore) and, with
--viz, colour overlays to <frames_dir>/viz/.
"""

import argparse
import os

import cv2
import numpy as np

from traversability import semantics
from traversability.learning.data import FrameFolder

DEFAULT_TEACHER = 'hf:facebook/mask2former-swin-large-mapillary-vistas-semantic'


def correct_with_geometry(classes, confidence, height, depth=None, camera_height=1.5, *, obstacle_height=0.15,
                          ground_tolerance=0.06, min_confidence=0.5, max_patch_fraction=0.02,
                          enclosure_fraction=0.75, ring=15, max_range=6.0, noise_coeff=0.01, noise_sigmas=3.0):
    """Teacher classes + height above ground -> training labels.

    With ``depth`` (metres), geometry is trusted only up to ``max_range`` and
    its height thresholds widen with distance (sigma_h ~ c * h_cam * z; c of
    0.01 matches a D435i measured on campus road, about twice the datasheet
    figure). Raised pixels override only a teacher "road" label -- a raised
    verge stays terrain, a curb stays sidewalk.
    """
    labels = classes.copy()
    valid = np.isfinite(height)
    tolerance = 0.0
    if depth is not None:
        valid &= np.isfinite(depth) & (depth < max_range)
        tolerance = noise_sigmas * noise_coeff * camera_height * np.nan_to_num(depth)
    flat = valid & (np.abs(height) < ground_tolerance + tolerance)
    labels[valid & (height > obstacle_height + tolerance) & (classes == semantics.ROAD)] = semantics.OTHER

    # Flat "other" blobs enclosed by flat road -> road.
    candidates = (flat & (classes == semantics.OTHER)).astype(np.uint8)
    flat_road = flat & (classes == semantics.ROAD)
    count, comp, stats, _ = cv2.connectedComponentsWithStats(candidates, connectivity=8)
    kernel = np.ones((3, 3), np.uint8)
    max_area = max_patch_fraction * classes.size
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] > max_area:
            continue
        x, y, w, h = (stats[i, k] for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH,
                                            cv2.CC_STAT_HEIGHT))
        x0, y0 = max(0, x - ring - 1), max(0, y - ring - 1)
        x1, y1 = min(classes.shape[1], x + w + ring + 1), min(classes.shape[0], y + h + ring + 1)
        blob = comp[y0:y1, x0:x1] == i
        border = cv2.dilate(blob.astype(np.uint8), kernel, iterations=ring).astype(bool) & ~blob
        judged = border & valid[y0:y1, x0:x1] & (labels[y0:y1, x0:x1] != semantics.OTHER)
        if judged.sum() and flat_road[y0:y1, x0:x1][judged].mean() >= enclosure_fraction:
            labels[y0:y1, x0:x1][blob] = semantics.ROAD

    labels[confidence < min_confidence] = semantics.IGNORE
    return labels


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('frames', nargs='+', help='frame folders from record_frames')
    ap.add_argument('--teacher', default=DEFAULT_TEACHER)
    ap.add_argument('--input-size', type=int, nargs=2, default=(1024, 576), metavar=('W', 'H'))
    ap.add_argument('--min-confidence', type=float, default=0.5)
    ap.add_argument('--max-range', type=float, default=6.0, help='trust depth geometry up to this distance (m)')
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--viz', action='store_true', help='also write overlays to <frames>/viz')
    args = ap.parse_args(argv)

    from traversability import segmentation
    teacher = segmentation.load(args.teacher, input_size=tuple(args.input_size))
    for root in args.frames:
        data = FrameFolder(root, require_labels=False)
        os.makedirs(os.path.join(root, 'labels'), exist_ok=True)
        if args.viz:
            os.makedirs(os.path.join(root, 'viz'), exist_ok=True)
        done = 0
        for i, name in enumerate(data.names):
            out = os.path.join(root, 'labels', name + '.png')
            if os.path.exists(out) and not args.overwrite:
                continue
            rgb = data.rgb(i)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            classes, confidence = teacher(bgr)
            meta = data.meta(i)
            up = np.asarray(meta['R'])[:, 2]
            camera_height = float(-up @ np.asarray(meta['t']))      # camera's distance above the plane
            labels = correct_with_geometry(classes, confidence, data.height(i), data.depth(i), camera_height,
                                           min_confidence=args.min_confidence, max_range=args.max_range)
            cv2.imwrite(out, labels)
            if args.viz:
                shown = np.where(labels[..., None] == semantics.IGNORE, 0,
                                 semantics.colorize(np.minimum(labels, 4)))
                viz = np.hstack([bgr, (0.5 * bgr + 0.5 * shown).astype(np.uint8)])
                cv2.imwrite(os.path.join(root, 'viz', name + '.jpg'), viz)
            done += 1
            if done % 25 == 0:
                print(f'{root}: {done} labelled', flush=True)
        print(f'{root}: {done} new labels ({len(data)} frames)')


if __name__ == '__main__':
    main()
