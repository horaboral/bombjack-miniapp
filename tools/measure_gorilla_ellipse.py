"""Measure the white ellipse the user drew on the new headless gorilla.
Output: center (cx, cy), radii (rx, ry) in body pixels, and the bounding box.
Also check the background color (corners)."""
import os
import shutil
import numpy as np
from PIL import Image

SRC = r"C:\Users\gru\Pictures\loj shavale\head removed 300px-Donkey_Kong2.jpg"
DST = r"D:\dsh workspace\dsh test project\assets\bodies\gorilla_headless_new.jpg"

shutil.copyfile(SRC, DST)
img = Image.open(DST).convert("RGB")
arr = np.array(img)
H, W = arr.shape[:2]
print(f"body: {W}x{H}")

# Corners for background color
print("corners:", arr[5, 5].tolist(), arr[5, W-5].tolist(),
      arr[H-5, 5].tolist(), arr[H-5, W-5].tolist())

# White mask: all channels > 235 (the drawn ellipse is pure white)
white = arr.min(axis=2) > 235
ys, xs = np.nonzero(white)
print(f"white px: {len(xs)}")
if len(xs):
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    print(f"bbox: x=[{x0},{x1}] y=[{y0},{y1}]  w={x1-x0} h={y1-y0}")
    print(f"center=({cx:.1f},{cy:.1f})  rx={rx:.1f} ry={ry:.1f}")
    # Sanity: fill ratio of bbox (ellipse ~= 0.785)
    print(f"fill ratio: {len(xs) / ((x1-x0)*(y1-y0)):.3f} (ellipse ~0.785)")
