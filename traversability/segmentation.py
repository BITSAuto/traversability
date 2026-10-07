"""Semantic segmentation backends, all reduced to the four traversability classes.

Every backend maps a BGR image (and, for RGB-D students, a height-above-
ground image) to per-pixel probabilities over ROAD / SIDEWALK / TERRAIN /
OTHER, so the ROS node, the benchmark and the auto-labeller don't care which
model is behind them:

  HFSegmenter        Hugging Face checkpoints (SegFormer, Mask2Former), torch.
                     Development, benchmarking, and the auto-labelling teacher.
  StudentSegmenter   Phase 3 models trained by traversability.learning, torch.
  TensorRTSegmenter  Any of the above exported to ONNX (export_onnx) and built
                     into a TensorRT engine; this is what runs on the Orin,
                     which has TensorRT but no torch. Uses libcudart through
                     ctypes, so it needs no CUDA Python package either.

Torch is imported lazily (torch-only code lives in traversability.learning),
so the TensorRT path works on machines without it.

Exported ONNX models take raw pixels (float32 RGB, 0..255, NCHW) plus an
optional height input in metres, and output our class probabilities at the
model's output resolution; normalisation, softmax and label aggregation are
baked into the graph.
"""

import ctypes
import json
import os
import time

import cv2
import numpy as np


HEIGHT_CLIP = 2.0   # m; the height channel is clipped to +/- this and scaled to +/- 1


def height_channel(height):
    """Normalise a height-above-ground image (metres, NaN = no depth)."""
    h = np.nan_to_num(np.asarray(height, np.float32), nan=0.0)
    return np.clip(h, -HEIGHT_CLIP, HEIGHT_CLIP) / HEIGHT_CLIP


class Segmenter:
    """Base: subclasses implement ``probs`` -> (4, h, w) at model resolution."""

    name = 'segmenter'
    uses_height = False

    def probs(self, bgr, height=None):
        raise NotImplementedError

    def __call__(self, bgr, height=None):
        """Classes (H, W) uint8 in 1..4 and confidence (H, W) float32."""
        p = self.probs(bgr, height)
        h, w = bgr.shape[:2]
        # Decide at 2x the model's output resolution, then upsample the
        # labels: a per-pixel argmax at full camera resolution costs tens of
        # milliseconds on the Orin's CPU for no gain at grid resolution.
        mh, mw = p.shape[1:]
        p = cv2.resize(np.ascontiguousarray(p.transpose(1, 2, 0)), (2 * mw, 2 * mh), interpolation=cv2.INTER_LINEAR)
        classes = (np.argmax(p, axis=-1) + 1).astype(np.uint8)
        confidence = p.max(axis=-1)
        return (cv2.resize(classes, (w, h), interpolation=cv2.INTER_NEAREST),
                cv2.resize(confidence, (w, h), interpolation=cv2.INTER_NEAREST))

    def timed(self, bgr, height=None):
        t0 = time.perf_counter()
        out = self(bgr, height)
        return out, time.perf_counter() - t0


def _resize_rgb(bgr, size):
    return cv2.cvtColor(cv2.resize(bgr, size, interpolation=cv2.INTER_LINEAR), cv2.COLOR_BGR2RGB)


# --------------------------------------------------------------------- torch
class _TorchCore:
    """Shared torch plumbing: wraps a model in the export-compatible head."""

    def __init__(self, module, input_size, device, fp16):
        import torch
        self.torch = torch
        self.device = torch.device(device if torch.cuda.is_available() or device == 'cpu' else 'cpu')
        self.dtype = torch.float16 if fp16 and self.device.type == 'cuda' else torch.float32
        self.module = module.to(self.device, self.dtype).eval()
        self.input_size = tuple(input_size)

    def run(self, bgr, height=None):
        torch = self.torch
        rgb = _resize_rgb(bgr, self.input_size)
        image = torch.from_numpy(rgb).permute(2, 0, 1)[None].to(self.device, self.dtype)
        args = [image]
        if height is not None:
            h = cv2.resize(height_channel(height), self.input_size, interpolation=cv2.INTER_NEAREST)
            args.append(torch.from_numpy(h)[None, None].to(self.device, self.dtype))
        with torch.inference_mode():
            return self.module(*args)[0].float().cpu().numpy()


class HFSegmenter(Segmenter):
    def __init__(self, model_id, input_size=(1024, 576), device='cuda', fp16=True):
        from traversability.learning.heads import build_hf_head
        head, self.label_names = build_hf_head(model_id)
        self.name = model_id.split('/')[-1]
        self.core = _TorchCore(head, input_size, device, fp16)

    def probs(self, bgr, height=None):
        return self.core.run(bgr)


class StudentSegmenter(Segmenter):
    def __init__(self, checkpoint, device='cuda', fp16=True):
        from traversability.learning.model import load_student
        head, meta = load_student(checkpoint)
        self.name = meta.get('name', os.path.basename(checkpoint))
        self.uses_height = meta['in_channels'] == 4
        self.core = _TorchCore(head, meta['input_size'], device, fp16)

    def probs(self, bgr, height=None):
        if self.uses_height and height is None:
            raise ValueError(f'{self.name} needs a height image')
        return self.core.run(bgr, height if self.uses_height else None)


# ------------------------------------------------------------------ TensorRT
class _CudaRuntime:
    """The handful of libcudart calls TensorRT inference needs."""

    H2D, D2H = 1, 2

    def __init__(self):
        for name in ('libcudart.so', 'libcudart.so.13', 'libcudart.so.12'):
            try:
                self.lib = ctypes.CDLL(name)
                break
            except OSError:
                continue
        else:
            raise OSError('libcudart not found')
        self.lib.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t]
        self.lib.cudaFree.argtypes = [ctypes.c_void_p]
        self.lib.cudaMemcpyAsync.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                             ctypes.c_int, ctypes.c_void_p]
        self.lib.cudaStreamCreate.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.lib.cudaStreamSynchronize.argtypes = [ctypes.c_void_p]

    def check(self, err, what):
        if err != 0:
            raise RuntimeError(f'{what} failed with CUDA error {err}')

    def malloc(self, nbytes):
        ptr = ctypes.c_void_p()
        self.check(self.lib.cudaMalloc(ctypes.byref(ptr), nbytes), 'cudaMalloc')
        return ptr

    def stream(self):
        s = ctypes.c_void_p()
        self.check(self.lib.cudaStreamCreate(ctypes.byref(s)), 'cudaStreamCreate')
        return s

    def copy(self, dst, src, nbytes, kind, stream):
        self.check(self.lib.cudaMemcpyAsync(dst, src, nbytes, kind, stream), 'cudaMemcpyAsync')

    def sync(self, stream):
        self.check(self.lib.cudaStreamSynchronize(stream), 'cudaStreamSynchronize')


class TensorRTSegmenter(Segmenter):
    """Runs an engine built from an export_onnx model (``trtexec --onnx ...``)."""

    def __init__(self, engine_path, meta_path=None):
        import tensorrt as trt
        meta_path = meta_path or os.path.splitext(engine_path)[0] + '.onnx.json'
        with open(meta_path) as f:
            meta = json.load(f)
        self.name = meta.get('name', os.path.basename(engine_path))
        self.input_size = tuple(meta['input_size'])
        self.uses_height = meta.get('height_input', False)

        self.cuda = _CudaRuntime()
        self.logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, 'rb') as f:
            self.engine = trt.Runtime(self.logger).deserialize_cuda_engine(f.read())
        if self.engine is None:
            raise RuntimeError(f'could not load TensorRT engine {engine_path}')
        self.context = self.engine.create_execution_context()
        self.stream = self.cuda.stream()
        self.host, self.device = {}, {}
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            shape = tuple(self.engine.get_tensor_shape(name))
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            self.host[name] = np.zeros(shape, dtype)
            self.device[name] = self.cuda.malloc(self.host[name].nbytes)
            self.context.set_tensor_address(name, self.device[name].value)
        self.inputs = [n for n in self.host if self.engine.get_tensor_mode(n) == trt.TensorIOMode.INPUT]

    def probs(self, bgr, height=None):
        rgb = _resize_rgb(bgr, self.input_size).astype(np.float32)
        self.host['image'][0] = rgb.transpose(2, 0, 1)
        if self.uses_height:
            if height is None:
                raise ValueError(f'{self.name} needs a height image')
            self.host['height'][0, 0] = cv2.resize(height_channel(height), self.input_size,
                                                   interpolation=cv2.INTER_NEAREST)
        for name in self.inputs:
            buf = np.ascontiguousarray(self.host[name])
            self.cuda.copy(self.device[name], buf.ctypes.data, buf.nbytes, self.cuda.H2D, self.stream)
        if not self.context.execute_async_v3(self.stream.value):
            raise RuntimeError('TensorRT execution failed')
        out = self.host['probs']
        self.cuda.copy(out.ctypes.data, self.device['probs'], out.nbytes, self.cuda.D2H, self.stream)
        self.cuda.sync(self.stream)
        return out[0].astype(np.float32)


def load(spec, **kwargs):
    """Backend from a spec string:
    ``hf:<model id>``, ``student:<checkpoint.pt>`` or ``trt:<engine>``."""
    kind, _, target = spec.partition(':')
    if kind == 'hf':
        return HFSegmenter(target, **kwargs)
    if kind == 'student':
        return StudentSegmenter(target, **{k: v for k, v in kwargs.items() if k != 'input_size'})
    if kind == 'trt':
        return TensorRTSegmenter(target)
    raise ValueError(f'unknown segmenter spec {spec!r}; use hf:, student: or trt:')
