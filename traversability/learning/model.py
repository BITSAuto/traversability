"""Phase 3 student models: a pretrained backbone with a 4-class head, taking
RGB or RGB + height above ground (RGB-D).

  segformer-b0 / segformer-b2   SegFormer initialised from the Cityscapes
                                checkpoints (road/sidewalk/terrain already
                                learned), head replaced with our 4 classes.
  dinov2-small / dinov2-base    DINOv2 features (frozen or fine-tuned) with a
                                linear head over the last four layers, as in
                                the DINOv2 paper's segmentation probe.

The height channel enters through the first patch embedding, which gets one
extra input channel initialised to zero -- so a fresh RGB-D student starts
out behaving exactly like the RGB model and learns how much to use height.
"""

import torch
import torch.nn.functional as F

from traversability import semantics
from traversability.learning.heads import ExportHead

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

ARCHS = {
    'segformer-b0': 'nvidia/segformer-b0-finetuned-cityscapes-1024-1024',
    'segformer-b2': 'nvidia/segformer-b2-finetuned-cityscapes-1024-1024',
    'dinov2-small': 'facebook/dinov2-small',
    'dinov2-base': 'facebook/dinov2-base',
}


def _widen_conv(conv, extra=1):
    """Copy of ``conv`` with ``extra`` more input channels, zero-initialised."""
    new = torch.nn.Conv2d(conv.in_channels + extra, conv.out_channels, conv.kernel_size, conv.stride,
                          conv.padding, bias=conv.bias is not None)
    with torch.no_grad():
        new.weight.zero_()
        new.weight[:, :conv.in_channels] = conv.weight
        if conv.bias is not None:
            new.bias.copy_(conv.bias)
    return new


class Student(torch.nn.Module):
    def __init__(self, arch='segformer-b0', in_channels=3, pretrained=True, freeze_backbone=False):
        super().__init__()
        from transformers import AutoConfig, Dinov2Model, SegformerForSemanticSegmentation
        self.arch = arch
        self.in_channels = in_channels
        model_id = ARCHS[arch]
        if arch.startswith('segformer'):
            names = {i: semantics.NAMES[i + 1] for i in range(semantics.NUM_CLASSES)}
            kw = dict(num_labels=semantics.NUM_CLASSES, id2label=names,
                      label2id={v: k for k, v in names.items()}, ignore_mismatched_sizes=True)
            self.net = (SegformerForSemanticSegmentation.from_pretrained(model_id, **kw) if pretrained else
                        SegformerForSemanticSegmentation(AutoConfig.from_pretrained(model_id, **kw)))
            seg = self.net.segformer
            # transformers >= 5 keeps the first patch embedding in stages[0];
            # older versions in encoder.patch_embeddings[0].
            emb = seg.stages[0].patch_embeddings if hasattr(seg, 'stages') else seg.encoder.patch_embeddings[0]
            if in_channels > 3:
                emb.proj = _widen_conv(emb.proj, in_channels - 3)
            self.stride = 4
        else:
            self.net = Dinov2Model.from_pretrained(model_id) if pretrained else \
                Dinov2Model(AutoConfig.from_pretrained(model_id))
            if in_channels > 3:
                pe = self.net.embeddings.patch_embeddings
                pe.projection = _widen_conv(pe.projection, in_channels - 3)
                pe.num_channels = in_channels
                self.net.config.num_channels = in_channels
            dim = self.net.config.hidden_size * 4
            self.head = torch.nn.Sequential(torch.nn.BatchNorm2d(dim),
                                            torch.nn.Conv2d(dim, semantics.NUM_CLASSES, 1))
            self.stride = self.net.config.patch_size
            if freeze_backbone:
                for p in self.net.parameters():
                    p.requires_grad = False
                if in_channels > 3:       # the new height weights must still learn
                    self.net.embeddings.patch_embeddings.projection.weight.requires_grad = True

    def forward(self, x, height=None):
        """``x``: normalised RGB (B, 3, H, W); ``height``: (B, 1, H, W) in
        [-1, 1] or None. Returns logits at 1/stride resolution."""
        if self.in_channels > 3:
            if height is None:
                height = torch.zeros_like(x[:, :1])
            x = torch.cat([x, height.to(x.dtype)], dim=1)
        if self.arch.startswith('segformer'):
            return self.net(pixel_values=x).logits
        b, _, h, w = x.shape
        out = self.net(pixel_values=x, output_hidden_states=True)
        gh, gw = h // self.stride, w // self.stride
        feats = [s[:, 1:1 + gh * gw] for s in out.hidden_states[-4:]]        # drop the CLS token
        f = torch.cat(feats, dim=-1).transpose(1, 2).reshape(b, -1, gh, gw)
        return self.head(f)

    def logits_full(self, x, height=None):
        """Logits upsampled to the input resolution (for the training loss)."""
        return F.interpolate(self.forward(x, height), size=x.shape[-2:], mode='bilinear', align_corners=False)


def save_student(path, model, input_size, extra=None):
    torch.save({'arch': model.arch, 'in_channels': model.in_channels, 'input_size': list(input_size),
                'state_dict': model.state_dict(), **(extra or {})}, path)


def load_student(path, map_location='cpu'):
    """(ExportHead taking raw pixels -> class probs, metadata dict)."""
    ckpt = torch.load(path, map_location=map_location, weights_only=False)
    model = Student(ckpt['arch'], ckpt['in_channels'], pretrained=False)
    model.load_state_dict(ckpt['state_dict'])
    meta = {k: v for k, v in ckpt.items() if k != 'state_dict'}
    meta.setdefault('name', f"student-{ckpt['arch']}{'-rgbd' if ckpt['in_channels'] > 3 else ''}")
    return ExportHead(model, IMAGENET_MEAN, IMAGENET_STD, student=True), meta
