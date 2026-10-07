"""Compare segmentation models on labelled frames.

  ros2 run traversability benchmark_models --data frames/campus_val \\
      --models hf:nvidia/segformer-b2-finetuned-cityscapes-1024-1024 student:students/b0/best.pt

Labels come from autolabel (or hand-corrected versions of them). Reports,
per model: IoU for each traversability class, mIoU, latency on this
machine, and two numbers that matter more than mIoU here:

  flat-road recall   share of flat (|h| < 6 cm) pixels labelled ROAD that the
                     model calls ROAD -- includes the paint/paper patches
                     autolabel turned into road; low means false "not road"
  forbidden recall   share of SIDEWALK + TERRAIN pixels the model calls
                     SIDEWALK or TERRAIN; low means it would drive onto them

Writes a markdown table to stdout (and --out if given).
"""

import argparse

import cv2
import numpy as np

from traversability import semantics
from traversability.learning.data import FrameFolder


def score(pred, labels, height):
    valid = labels != semantics.IGNORE
    n = semantics.NUM_CLASSES
    conf = np.bincount((labels[valid].astype(np.int64) - 1) * n + (pred[valid].astype(np.int64) - 1),
                       minlength=n * n).reshape(n, n)
    flat_road = valid & (labels == semantics.ROAD) & np.isfinite(height) & (np.abs(height) < 0.06)
    forbidden = valid & np.isin(labels, semantics.FORBIDDEN)
    return conf, (np.count_nonzero(pred[flat_road] == semantics.ROAD), np.count_nonzero(flat_road)), \
        (np.count_nonzero(np.isin(pred[forbidden], semantics.FORBIDDEN)), np.count_nonzero(forbidden))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', nargs='+', required=True)
    ap.add_argument('--models', nargs='+', required=True, help='specs: hf:..., student:..., trt:...')
    ap.add_argument('--input-size', type=int, nargs=2, default=(1024, 576), metavar=('W', 'H'))
    ap.add_argument('--every', type=int, default=1, help='use every n-th frame')
    ap.add_argument('--tail', type=float, default=0.0,
                    help='only the last fraction of each folder (matches train_student --val-tail)')
    ap.add_argument('--out')
    args = ap.parse_args(argv)

    from traversability import segmentation
    folders = [FrameFolder(r) for r in args.data]
    frames = [(f, i) for f in folders for i in range(0, len(f), args.every)
              if i >= len(f) * (1 - args.tail)]
    rows = []
    for spec in args.models:
        seg = segmentation.load(spec, input_size=tuple(args.input_size))
        n = semantics.NUM_CLASSES
        conf, fr, fb, times = np.zeros((n, n), np.int64), [0, 0], [0, 0], []
        for f, i in frames:
            rgb, height, labels = f[i]
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            (pred, _), dt = seg.timed(bgr, height if seg.uses_height else None)
            times.append(dt)
            c, a, b = score(pred, labels, height)
            conf += c
            fr = [fr[0] + a[0], fr[1] + a[1]]
            fb = [fb[0] + b[0], fb[1] + b[1]]
        tp = np.diag(conf).astype(float)
        iou = tp / np.maximum(conf.sum(0) + conf.sum(1) - tp, 1)
        rows.append((seg.name, iou, iou.mean(), fr[0] / max(fr[1], 1), fb[0] / max(fb[1], 1),
                     1000 * np.median(times[1:] or times)))
        print(f'{seg.name}: mIoU {iou.mean():.3f}', flush=True)
        del seg

    names = [semantics.NAMES[i] for i in range(1, semantics.NUM_CLASSES + 1)]
    lines = [f'Frames: {len(frames)} from {", ".join(args.data)}', '',
             '| model | ' + ' | '.join(f'IoU {c}' for c in names) +
             ' | mIoU | flat-road recall | forbidden recall | ms/frame |',
             '|' + '---|' * (len(names) + 5)]
    for name, iou, miou, frr, fbr, ms in rows:
        lines.append(f'| {name} | ' + ' | '.join(f'{v:.3f}' for v in iou) +
                     f' | {miou:.3f} | {frr:.3f} | {fbr:.3f} | {ms:.0f} |')
    report = '\n'.join(lines)
    print(report)
    if args.out:
        with open(args.out, 'w') as f:
            f.write(report + '\n')


if __name__ == '__main__':
    main()
