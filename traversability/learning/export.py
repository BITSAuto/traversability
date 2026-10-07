"""Export a segmentation model to ONNX for TensorRT on the Orin.

  ros2 run traversability export_model hf:nvidia/segformer-b2-finetuned-cityscapes-1024-1024 segformer_b2.onnx
  ros2 run traversability export_model student:students/b0_rgbd/best.pt b0_rgbd.onnx

The ONNX model takes raw RGB (float32 0..255, NCHW, input_size) and, for
RGB-D students, a normalised height input; it outputs traversability-class
probabilities. A ``<out>.json`` sidecar records sizes and inputs. On the
Orin, build the engine with

  /usr/src/tensorrt/bin/trtexec --onnx=<out>.onnx --saveEngine=<out>.engine --fp16

and run it with ``model:=trt:<out>.engine`` (keep the .onnx.json next to it).
"""

import argparse


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('model', help='hf:<model id> or student:<checkpoint.pt>')
    ap.add_argument('out', help='output .onnx path')
    ap.add_argument('--input-size', type=int, nargs=2, metavar=('W', 'H'),
                    help='default: 1024x576 for HF models, the training input size for students')
    args = ap.parse_args(argv)

    from traversability.learning.heads import build_hf_head, export_onnx
    kind, _, target = args.model.partition(':')
    if kind == 'hf':
        head, _ = build_hf_head(target)
        size = tuple(args.input_size or (1024, 576))
        export_onnx(head, args.out, size, meta={'name': target.split('/')[-1]})
    elif kind == 'student':
        from traversability.learning.model import load_student
        head, meta = load_student(target)
        size = tuple(args.input_size or meta['input_size'])
        export_onnx(head, args.out, size, with_height=meta['in_channels'] > 3, meta={'name': meta['name']})
    else:
        raise SystemExit('model must be hf:<id> or student:<checkpoint>')
    print(f'exported {args.out} ({size[0]}x{size[1]})')


if __name__ == '__main__':
    main()
