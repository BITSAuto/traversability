"""Torch-side model heads: wrap any segmentation core so it takes raw pixels
and returns traversability-class probabilities, and export that to ONNX."""

import json

import torch

from traversability import semantics


def build_hf_head(model_id):
    """(torch module taking raw RGB -> class probs, label names) for an HF checkpoint."""
    from huggingface_hub import hf_hub_download
    from transformers import AutoConfig, AutoModelForSemanticSegmentation, AutoModelForUniversalSegmentation

    config = AutoConfig.from_pretrained(model_id)
    names = [config.id2label[i] for i in range(len(config.id2label))]
    # Read normalisation straight from the preprocessor config rather than
    # through AutoImageProcessor, which needs a newer Pillow than Ubuntu 22.04's.
    with open(hf_hub_download(model_id, 'preprocessor_config.json')) as f:
        processor = json.load(f)
    mask2former = config.model_type in ('mask2former', 'maskformer', 'oneformer')
    model = (AutoModelForUniversalSegmentation if mask2former else AutoModelForSemanticSegmentation
             ).from_pretrained(model_id)
    return ExportHead(model, processor['image_mean'], processor['image_std'],
                      semantics.aggregation_matrix(names), universal=mask2former), names


class ExportHead(torch.nn.Module):
    """Raw pixels in, traversability-class probabilities out (ONNX-exportable).

    ``core`` is either an HF model (semantic or universal/mask-query style) or
    a phase 3 student returning logits directly over our classes
    (``aggregation`` None).
    """

    def __init__(self, core, mean, std, aggregation=None, universal=False, student=False):
        super().__init__()
        self.core = core
        self.universal = universal
        self.student = student
        self.register_buffer('mean', torch.tensor(mean, dtype=torch.float32).view(1, 3, 1, 1))
        self.register_buffer('std', torch.tensor(std, dtype=torch.float32).view(1, 3, 1, 1))
        agg = None if aggregation is None else torch.tensor(aggregation)
        self.register_buffer('aggregation', agg)

    def forward(self, image, height=None):
        x = (image / 255.0 - self.mean.to(image.dtype)) / self.std.to(image.dtype)
        if self.student:
            logits = self.core(x, height)
            return torch.softmax(logits, dim=1)
        if self.universal:
            out = self.core(pixel_values=x)
            cls = torch.softmax(out.class_queries_logits, dim=-1)[..., :-1]       # drop "no object"
            masks = torch.sigmoid(out.masks_queries_logits)
            p = torch.einsum('bqc,bqhw->bchw', cls, masks)
            p = p / p.sum(dim=1, keepdim=True).clamp_min(1e-6)
        else:
            p = torch.softmax(self.core(pixel_values=x).logits, dim=1)
        return torch.einsum('kc,bchw->bkhw', self.aggregation.to(p.dtype), p)


def export_onnx(head, path, input_size, with_height=False, meta=None):
    """Export an ExportHead to ONNX plus a ``<path>.json`` sidecar."""
    head = head.float().cpu().eval()
    w, h = input_size
    args = [torch.zeros(1, 3, h, w)]
    names = ['image']
    if with_height:
        args.append(torch.zeros(1, 1, h, w))
        names.append('height')
    torch.onnx.export(head, tuple(args), path, input_names=names, output_names=['probs'],
                      opset_version=17, dynamo=False)
    with open(path + '.json', 'w') as f:
        json.dump(dict(meta or {}, input_size=[w, h], height_input=with_height,
                       classes=[semantics.NAMES[i] for i in range(1, semantics.NUM_CLASSES + 1)]), f, indent=2)
