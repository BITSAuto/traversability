#!/usr/bin/env python3
"""Regenerate the test-scene textures in worlds/textures (deterministic)."""

import os

import cv2
import numpy as np

OUT = os.path.join(os.path.dirname(__file__), '..', 'worlds', 'textures')


def newspaper(size=512):
    rng = np.random.default_rng(1)
    img = np.full((size, size, 3), 228, np.uint8)
    img = (img + rng.normal(0, 4, img.shape)).clip(0, 255).astype(np.uint8)
    cv2.putText(img, 'DAILY NEWS', (24, 70), cv2.FONT_HERSHEY_TRIPLEX, 2.0, (25, 25, 25), 4, cv2.LINE_AA)
    cv2.line(img, (20, 90), (size - 20, 90), (40, 40, 40), 3)
    cv2.rectangle(img, (280, 110), (size - 24, 300), (90, 90, 90), -1)   # photo
    columns = [(24, 260), (280, size - 24)]
    for i, (x0, x1) in enumerate(columns):
        y = 320 if i else 110
        while y < size - 20:
            width = int((x1 - x0) * rng.uniform(0.6, 1.0))
            cv2.line(img, (x0, y), (x0 + width, y), (70, 70, 70), 3)
            y += 14
    return img


def grass(size=512):
    rng = np.random.default_rng(2)
    base = np.array([40, 120, 60], np.float32)               # BGR
    noise = cv2.GaussianBlur(rng.normal(0, 1, (size, size)).astype(np.float32), (0, 0), 2)
    fine = rng.normal(0, 1, (size, size)).astype(np.float32)
    shade = 1.0 + 0.25 * noise / noise.std() + 0.15 * fine
    return (base[None, None] * shade[..., None]).clip(0, 255).astype(np.uint8)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cv2.imwrite(os.path.join(OUT, 'newspaper.png'), newspaper(), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    cv2.imwrite(os.path.join(OUT, 'grass.jpg'), grass(256), [cv2.IMWRITE_JPEG_QUALITY, 85])
