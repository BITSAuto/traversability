"""Train a phase 3 student on auto-labelled frames (and optionally IDD).

  ros2 run traversability train_student --data frames/campus_1 frames/sim_1 \\
      --arch segformer-b0 --rgbd --out students/b0_rgbd

Validation uses every ``--val-every``-th frame of the frame folders, or with
``--val-tail`` the last part of each recording (never trained on). IDD, if
given with --idd, adds its train split to training (no depth, so RGB-D
students see it with the height channel empty).

Writes <out>/best.pt (by validation mIoU), <out>/last.pt and
<out>/log.csv; --export also writes <out>/best.onnx (+ .json) for TensorRT.
"""

import argparse
import csv
import os
import time

import numpy as np
import torch
import torch.nn.functional as F

from traversability import semantics
from traversability.learning.data import IDD, FrameFolder, augment
from traversability.learning.model import IMAGENET_MEAN, IMAGENET_STD, Student, load_student, save_student
from traversability.segmentation import height_channel


class Samples(torch.utils.data.Dataset):
    """(dataset, index) pairs -> augmented, normalised tensors."""

    def __init__(self, items, size, train, seed=0):
        self.items, self.size, self.train, self.seed = items, size, train, seed
        self.mean = np.array(IMAGENET_MEAN, np.float32) * 255
        self.std = np.array(IMAGENET_STD, np.float32) * 255

    def __len__(self):
        return len(self.items)

    def __getitem__(self, k):
        ds, i = self.items[k]
        rgb, height, labels = ds[i]
        if self.train:
            rng = np.random.default_rng((self.seed, k, int(time.time() * 1e6) % 2**31))
            rgb, height, labels = augment(rgb, height, labels, self.size, rng)
        else:
            import cv2
            rgb = cv2.resize(rgb, self.size, interpolation=cv2.INTER_LINEAR)
            height = cv2.resize(height, self.size, interpolation=cv2.INTER_NEAREST)
            labels = cv2.resize(labels, self.size, interpolation=cv2.INTER_NEAREST)
        x = torch.from_numpy(((rgb.astype(np.float32) - self.mean) / self.std).transpose(2, 0, 1))
        h = torch.from_numpy(height_channel(height))[None]
        # Labels: 1..4 -> 0..3, everything else ignored.
        y = labels.astype(np.int64) - 1
        y[(labels < 1) | (labels > semantics.NUM_CLASSES)] = 255
        return x, h, torch.from_numpy(y)


def confusion(pred, target, n=semantics.NUM_CLASSES):
    keep = target != 255
    return torch.bincount(target[keep] * n + pred[keep], minlength=n * n).reshape(n, n)


def iou_from(conf):
    conf = conf.double()
    tp = conf.diag()
    iou = tp / (conf.sum(0) + conf.sum(1) - tp).clamp_min(1)
    return iou.cpu().numpy()


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    conf = torch.zeros(semantics.NUM_CLASSES, semantics.NUM_CLASSES, dtype=torch.long, device=device)
    for x, h, y in loader:
        x, h, y = x.to(device), h.to(device), y.to(device)
        with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
            pred = model.logits_full(x, h).argmax(1)
        conf += confusion(pred.flatten(), y.flatten())
    model.train()
    return iou_from(conf)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', nargs='*', default=[], help='auto-labelled frame folders')
    ap.add_argument('--idd', help='IDD Segmentation root (level3Ids labels created)')
    ap.add_argument('--arch', default='segformer-b0',
                    choices=['segformer-b0', 'segformer-b2', 'dinov2-small', 'dinov2-base'])
    ap.add_argument('--rgbd', action='store_true', help='add the height-above-ground input channel')
    ap.add_argument('--freeze-backbone', action='store_true', help='DINOv2: train the head only')
    ap.add_argument('--crop', type=int, nargs=2, default=None, metavar=('W', 'H'),
                    help='training crop (default 512x512; 518x518 for DINOv2)')
    ap.add_argument('--input-size', type=int, nargs=2, default=None, metavar=('W', 'H'),
                    help='inference size stored with the model (default 1024x576; 1022x574 for DINOv2)')
    ap.add_argument('--steps', type=int, default=4000)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--lr', type=float, default=6e-5)
    ap.add_argument('--val-every', type=int, default=10)
    ap.add_argument('--val-tail', type=float, default=0.0,
                    help='hold out this fraction at the end of each folder instead of every n-th frame '
                         '(use for real recordings, whose neighbouring frames are near-duplicates)')
    ap.add_argument('--eval-interval', type=int, default=500)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--out', required=True)
    ap.add_argument('--export', action='store_true', help='export best.onnx at the end')
    args = ap.parse_args(argv)

    dino = args.arch.startswith('dinov2')
    crop = tuple(args.crop or ((518, 518) if dino else (512, 512)))
    input_size = tuple(args.input_size or ((1022, 574) if dino else (1024, 576)))
    os.makedirs(args.out, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    train_items, val_items = [], []
    for root in args.data:
        ds = FrameFolder(root)
        for i in range(len(ds)):
            if args.val_tail > 0:      # hold out the end of each recording (frames are time-ordered)
                held_out = i >= len(ds) * (1 - args.val_tail)
            else:
                held_out = i % args.val_every == 0
            (val_items if held_out else train_items).append((ds, i))
    if args.idd:
        idd = IDD(args.idd, 'train')
        train_items += [(idd, i) for i in range(len(idd))]
    if not train_items:
        raise SystemExit('no training data: pass --data (auto-labelled) and/or --idd')
    print(f'train {len(train_items)} samples, val {len(val_items)}; crop {crop}, device {device}')

    loader = torch.utils.data.DataLoader(Samples(train_items, crop, True), batch_size=args.batch, shuffle=True,
                                         num_workers=args.workers, drop_last=True, persistent_workers=True)
    val_loader = torch.utils.data.DataLoader(Samples(val_items, input_size, False), batch_size=2,
                                             num_workers=args.workers) if val_items else None

    model = Student(args.arch, 4 if args.rgbd else 3, freeze_backbone=args.freeze_backbone).to(device)
    # The new head learns faster than the pretrained backbone.
    head_params = [p for n, p in model.named_parameters() if p.requires_grad and
                   ('decode_head' in n or n.startswith('head.'))]
    head_ids = {id(p) for p in head_params}
    body_params = [p for p in model.parameters() if p.requires_grad and id(p) not in head_ids]
    opt = torch.optim.AdamW([{'params': body_params, 'lr': args.lr},
                             {'params': head_params, 'lr': args.lr * 10}], weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (1 - s / args.steps) ** 0.9)
    scaler = torch.amp.GradScaler(enabled=device.type == 'cuda')

    best, step, t0 = -1.0, 0, time.time()
    log = open(os.path.join(args.out, 'log.csv'), 'w', newline='')
    writer = csv.writer(log)
    writer.writerow(['step', 'loss', 'miou'] + [semantics.NAMES[i] for i in range(1, semantics.NUM_CLASSES + 1)])
    losses = []
    while step < args.steps:
        for x, h, y in loader:
            x, h, y = x.to(device, non_blocking=True), h.to(device), y.to(device)
            with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
                loss = F.cross_entropy(model.logits_full(x, h if args.rgbd else None).float(), y, ignore_index=255)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            losses.append(loss.item())
            step += 1
            if step % 50 == 0:
                print(f'step {step}/{args.steps} loss {np.mean(losses[-50:]):.4f} '
                      f'({(time.time() - t0) / step:.2f} s/step)', flush=True)
            if step % args.eval_interval == 0 or step == args.steps:
                iou = evaluate(model, val_loader, device) if val_loader else np.full(semantics.NUM_CLASSES, np.nan)
                miou = float(np.nanmean(iou))
                writer.writerow([step, np.mean(losses[-50:]), miou] + list(iou))
                log.flush()
                print(f'  val mIoU {miou:.3f}  ' + '  '.join(
                    f'{semantics.NAMES[i + 1]} {v:.3f}' for i, v in enumerate(iou)), flush=True)
                meta = {'name': f"student-{args.arch}{'-rgbd' if args.rgbd else ''}", 'step': step, 'miou': miou}
                save_student(os.path.join(args.out, 'last.pt'), model, input_size, meta)
                if miou > best or not val_loader:
                    best = miou
                    save_student(os.path.join(args.out, 'best.pt'), model, input_size, meta)
            if step >= args.steps:
                break
    log.close()
    print(f'done: best val mIoU {best:.3f} -> {os.path.join(args.out, "best.pt")}')

    if args.export:
        from traversability.learning.heads import export_onnx
        head, meta = load_student(os.path.join(args.out, 'best.pt'))
        export_onnx(head, os.path.join(args.out, 'best.onnx'), input_size, with_height=args.rgbd,
                    meta={'name': meta['name']})
        print('exported', os.path.join(args.out, 'best.onnx'))


if __name__ == '__main__':
    main()
