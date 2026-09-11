"""Locate the headless patch on the roach body: white pixels that are
surrounded by (near) non-white pixels (the patch), vs the outer white
background. Print the patch bbox and overlay it on the body."""
import os
import numpy as np
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
body = Image.open(os.path.join(WS, "assets", "bodies", "roach_headless.jpg")).convert("RGB")
arr = np.array(body, dtype=np.int16)
white = (arr.min(axis=2) > 235)

# Flood-fill from the border to find the background white; the remainder
# (white pixels not reachable from the border) = the patch.
H, W = white.shape
from collections import deque
bg = np.zeros_like(white, dtype=bool)
q = deque()
for x in range(W):
    for y in (0, H - 1):
        if white[y, x] and not bg[y, x]:
            bg[y, x] = True; q.append((y, x))
for y in range(H):
    for x in (0, W - 1):
        if white[y, x] and not bg[y, x]:
            bg[y, x] = True; q.append((y, x))
while q:
    y, x = q.popleft()
    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W and white[ny, nx] and not bg[ny, nx]:
            bg[ny, nx] = True; q.append((ny, nx))

patch = white & ~bg
ys, xs = np.nonzero(patch)
print(f"patch pixels: {len(xs)}")
if len(xs):
    print(f"patch bbox: x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}] "
          f"w={xs.max()-xs.min()+1} h={ys.max()-ys.min()+1} center=({(xs.min()+xs.max())/2:.0f},{(ys.min()+ys.max())/2:.0f})")
    ov = body.copy()
    d = ImageDraw.Draw(ov)
    d.rectangle([xs.min(), ys.min(), xs.max(), ys.max()], outline=(255, 0, 0), width=3)
    ov.save(os.path.join(WS, "assets", "preview", "patch_overlay.png"))
    print("saved patch_overlay.png")
