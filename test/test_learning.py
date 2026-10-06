import numpy as np
import pytest

from traversability import semantics
from traversability.learning.autolabel import correct_with_geometry
from traversability.learning.data import IDD_LEVEL3_NAMES, augment, height_image, paste_clutter
from traversability.semantics import IGNORE, OTHER, ROAD, TERRAIN


def scene(h=120, w=160):
    classes = np.full((h, w), ROAD, np.uint8)
    height = np.zeros((h, w), np.float32)
    conf = np.ones((h, w), np.float32)
    return classes, height, conf


def test_flat_other_patch_on_road_becomes_road():
    classes, height, conf = scene()
    classes[60:70, 70:85] = OTHER                       # newspaper: flat, called "other"
    labels = correct_with_geometry(classes, conf, height)
    assert np.all(labels[60:70, 70:85] == ROAD)


def test_raised_or_unenclosed_other_stays_other():
    classes, height, conf = scene()
    classes[60:70, 70:85] = OTHER
    height[60:70, 70:85] = 0.4                           # a box: above ground
    classes[:, :40] = TERRAIN
    classes[30:40, 5:20] = OTHER                         # flat but on the verge
    labels = correct_with_geometry(classes, conf, height)
    assert np.all(labels[60:70, 70:85] == OTHER)
    assert np.all(labels[30:40, 5:20] == OTHER)


def test_obstacle_called_road_becomes_other_and_low_confidence_ignored():
    classes, height, conf = scene()
    height[10:20, 10:20] = 0.5
    conf[100:, :] = 0.2
    labels = correct_with_geometry(classes, conf, height)
    assert np.all(labels[10:20, 10:20] == OTHER)
    assert np.all(labels[100:, :] == IGNORE)


def test_idd_level3_mapping():
    lut = semantics.class_lut(IDD_LEVEL3_NAMES)
    assert len(IDD_LEVEL3_NAMES) == 26
    assert lut[0] == ROAD and lut[1] == ROAD                       # road, drivable fallback
    assert lut[2] == semantics.SIDEWALK and lut[13] == semantics.SIDEWALK   # sidewalk, curb
    assert lut[3] == TERRAIN and lut[24] == TERRAIN               # non-drivable fallback, vegetation
    assert lut[9] == OTHER                                        # car


def test_height_image_flat_ground():
    # Camera 1.5 m above ground looking forward; ground frame -> camera optical.
    R = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)
    t = np.array([0.0, 1.5, 0.0])
    K = [500, 0, 320, 0, 500, 240, 0, 0, 1]
    v = np.arange(480)[:, None].repeat(640, 1).astype(np.float32)
    with np.errstate(divide='ignore'):
        depth = np.where(v > 240, 1.5 * 500 / (v - 240), np.nan).astype(np.float32)   # ground rows
    h = height_image(depth, K, R, t)
    assert np.nanmax(np.abs(h[300:])) < 1e-3


def test_augment_and_clutter_keep_labels():
    rng = np.random.default_rng(0)
    rgb = np.full((360, 640, 3), 60, np.uint8)
    labels = np.full((360, 640), ROAD, np.uint8)
    labels[:100] = OTHER
    pasted = paste_clutter(rgb, labels, rng)
    assert np.any(pasted != rgb)
    assert np.all(pasted[:100] == rgb[:100])                       # only road pixels change
    out_rgb, out_h, out_l = augment(rgb, np.zeros((360, 640), np.float32), labels, (256, 128), rng)
    assert out_rgb.shape == (128, 256, 3) and out_h.shape == out_l.shape == (128, 256)
    assert set(np.unique(out_l)) <= {ROAD, OTHER}


def test_student_forward_shapes():
    torch = pytest.importorskip('torch')
    pytest.importorskip('transformers')
    from traversability.learning.model import Student
    for arch in ('segformer-b0', 'dinov2-small'):
        m = Student(arch, in_channels=4, pretrained=False).eval()
        size = (224, 224) if arch.startswith('dinov2') else (128, 128)
        x = torch.zeros(1, 3, *size)
        with torch.no_grad():
            out = m.logits_full(x, torch.zeros(1, 1, *size))
        assert out.shape == (1, semantics.NUM_CLASSES, *size)
