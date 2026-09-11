"""Compare the full cockroach body with the headless version to find
the exact region that was removed (the head patch). Save an overlay."""
import os
import numpy as np
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
full_img = Image.open(os.path.join(WS, "assets", "bodies", "cockroach_full.png")).convert("RGB")
headless_img = Image.open(os.path.join(WS, "assets", "bodies", "roach_headless.jpg")).convert("RGB")
full_img = full_img.resize(headless_img.size, Image.LANCZOS)
full = np.array(full_img, dtype=np.int16)
headless = np.array(headless_img, dtype=np.int16)

# Regions where the two differ significantly = the removed head
diff = np.abs(full - headless).max(axis=2)
mask = diff > 80
ys, xs = np.nonzero(mask)
if len(xs):
    print(f"diff region: x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}] "
          f"w={xs.max()-xs.min()+1} h={ys.max()-ys.min()+1} "
          f"center=({(xs.min()+xs.max())/2:.0f},{(ys.min()+ys.max())/2:.0f})")
    # Visualize
    ov = headless_img.copy()
    d = ImageDraw.Draw(ov)
    d.rectangle([xs.min(), ys.min(), xs.max(), ys.max()], outline=(255, 0, 0), width=4)
    ov.save(os.path.join(WS, "assets", "preview", "head_diff.png"))
    print("saved head_diff.png")
else:
    print("no significant diff found")
