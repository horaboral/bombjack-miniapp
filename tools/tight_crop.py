"""Tight face crops: measure content bbox from a rembg matte on the mid frame,
apply the same tight box to all 54 frames (camera is near-static)."""
import os
import numpy as np
from PIL import Image
from rembg import new_session, remove

WS = r"D:\dsh workspace\dsh test project"
loose = os.path.join(WS, "assets", "faces")
tight_dir = os.path.join(WS, "assets", "faces_tight")
os.makedirs(tight_dir, exist_ok=True)

session = new_session("isnet-general-use")

def content_box(fg_rgba, pad=8, min_frac=0.02):
    a = np.array(fg_rgba)[..., 3]
    thr = a.max() * min_frac
    ys, xs = np.where(a > thr)
    if len(xs) == 0:
        return None
    h, w = a.shape
    x0 = max(0, xs.min() - pad); x1 = min(w, xs.max() + 1 + pad)
    y0 = max(0, ys.min() - pad); y1 = min(h, ys.max() + 1 + pad)
    return (x0, y0, x1, y1)

for name in ("left", "right"):
    # matte the mid frame to find the face content box
    mid = Image.open(os.path.join(loose, name, "f_027.png")).convert("RGB")
    fg = remove(mid, session=session)
    box = content_box(fg)
    print(name, "content box in 400x400:", box)
    if not box:
        continue
    x0, y0, x1, y1 = box
    # make it a square (faces are square-ish), expand to the larger dimension
    bw, bh = x1 - x0, y1 - y0
    s = max(bw, bh)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0s = max(0, cx - s // 2); y0s = max(0, cy - s // 2)
    x1s = min(400, x0s + s); y1s = min(400, y0s + s)
    # re-square if clamped
    s2 = min(x1s - x0s, y1s - y0s)
    box_sq = (x0s, y0s, x0s + s2, y0s + s2)
    print(name, "tight square box:", box_sq, "size", s2)

    os.makedirs(os.path.join(tight_dir, name), exist_ok=True)
    for i in range(1, 55):
        im = Image.open(os.path.join(loose, name, f"f_{i:03d}.png")).convert("RGB")
        im.crop(box_sq).save(os.path.join(tight_dir, name, f"f_{i:03d}.png"))
    print(name, "tight frames written:", s2)
print("done")
