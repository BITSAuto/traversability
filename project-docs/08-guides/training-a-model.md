# Training a model

```bash
ros2 run traversability autolabel <frames_dir> --viz                       # teacher + geometry labels; check viz/
ros2 run traversability train_student --data <dir1> <dir2> [--idd <IDD root>] \
    --arch segformer-b0 --rgbd --out <out_dir> --export [--val-tail 0.25]
ros2 run traversability benchmark_models --data <dirs> --tail 0.25 \
    --models student:<out_dir>/best.pt hf:nvidia/segformer-b0-finetuned-cityscapes-1024-1024
```
- Look at the `viz/` overlays and hand-correct labels where it matters
  (verges, sidewalks).
- For recordings use `--val-tail`/`--tail` (time split), not every n-th
  frame.
- Architectures: `segformer-b0`, `segformer-b2`, `dinov2-small`,
  `dinov2-base`. `--rgbd` adds the height channel.
- 3000 steps of B0 RGB-D takes ~25 min on an RTX 3060.
- Record what you trained, on what, and the scores in
  [09-testing-and-results](../09-testing-and-results/README.md) and the
  worklog, and where the checkpoint is stored.
