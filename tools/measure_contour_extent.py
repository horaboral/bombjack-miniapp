"""Measure the actual extent of the user-drawn contours (min/max x/y)
to get the true head size, not the PCA-inflated radii."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = Image.open(marked_path).convert("RGB")
arr = np.array(img, dtype=np.int16)

# Use moderate thresholds that catch the hand-drawn line
# Red: R > 130, G < 100, B < 100
red_mask = (arr[:, :, 0] > 130) & (arr[:, :, 1] < 100) & (arr[:, :, 2] < 100)
# Blue: B > 120, R < 110, G < 130
blue_mask = (arr[:, :, 2] > 120) & (arr[:, :, 0] < 110) & (arr[:, :, 1] < 130)

for name, mask in [("left", red_mask), ("right", blue_mask)]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        print(f"{name}: no pixels"); continue
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    print(f"{name}: {len(xs)} px")
    print(f"  extent: x=[{x0},{x1}] y=[{y0},{y1}] w={x1-x0} h={y1-y0}")
    print(f"  center=({cx:.1f},{cy:.1f}) rx={rx:.1f} ry={ry:.1f}")
    # Compare to PCA fit
    print(f"  PCA fit: rx=234 ry=294 (left) or rx=240 ry=283 (right)")

print("done")
