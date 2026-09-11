"""Detect the video's circular frame (photo boundary) in the raw frame:
non-black pixel extent, per row/col."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
raw = np.array(Image.open(os.path.join(WS, "assets", "raw", "raw_f001.png")).convert("RGB"), dtype=np.int16)
lum = raw.mean(axis=2)
# Non-black mask: any channel > 30
nonblack = (raw.max(axis=2) > 30)
ys, xs = np.nonzero(nonblack)
print(f"non-black extent: x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}]")
cx = (xs.min() + xs.max()) / 2
cy = (ys.min() + ys.max()) / 2
r_x = (xs.max() - xs.min()) / 2
r_y = (ys.max() - ys.min()) / 2
print(f"center=({cx:.0f},{cy:.0f}) r_x={r_x:.0f} r_y={r_y:.0f}")
# Per-row extents to see the circle profile
for y in [100, 200, 300, 400, 500, 600, 700]:
    row = np.nonzero(nonblack[y])[0]
    if len(row) > 0:
        print(f"  y={y}: x=[{row.min()},{row.max()}] w={row.max()-row.min()}")
