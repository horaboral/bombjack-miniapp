"""Measure the white headless patch on the roach body by scanning the
region above the brown collar. The collar is the first row (from top)
where most pixels are brown (R>100, G<100, B<80)."""
import os
import numpy as np
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
body = Image.open(os.path.join(WS, "assets", "bodies", "roach_headless.jpg")).convert("RGB")
arr = np.array(body, dtype=np.int16)
H, W = arr.shape[:2]

# Find the collar row: first row from top where >30% of pixels are brown
brown = (arr[:, :, 0] > 100) & (arr[:, :, 1] < 110) & (arr[:, :, 2] < 90)
collar_row = None
for y in range(H):
    if brown[y].mean() > 0.30:
        collar_row = y
        break
print(f"collar row: {collar_row}")

# The patch is white pixels in rows [0, collar_row]
region = arr[:collar_row]
white = (region.min(axis=2) > 230)
ys, xs = np.nonzero(white)
if len(xs):
    print(f"patch (rows 0-{collar_row}): x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}] "
          f"w={xs.max()-xs.min()+1} h={ys.max()-ys.min()+1} center=({(xs.min()+xs.max())/2:.0f},{(ys.min()+ys.max())/2:.0f})")
    ov = body.copy()
    d = ImageDraw.Draw(ov)
    d.rectangle([xs.min(), ys.min(), xs.max(), ys.max()], outline=(255, 0, 0), width=4)
    d.line([(xs.max()+5, ys.min()), (xs.max()+5, ys.max())], fill=(0, 255, 0), width=2)
    ov.save(os.path.join(WS, "assets", "preview", "roach_patch_measured.png"))
    print("saved roach_patch_measured.png")
