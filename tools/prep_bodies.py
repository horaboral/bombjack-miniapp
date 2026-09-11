"""Prepare body assets: key out white bg, then produce headless versions + previews.
- Gorilla (Donkey Kong PNG): white background -> alpha via white-key + edge feather.
- Cockroach (webp): check its background, key if needed.
Also crop each to its content bbox and save full + headless previews."""
import os
import numpy as np
import cv2
from PIL import Image, ImageFilter

src_dir = r"C:\Users\gru\Pictures\loj shavale"
out_dir = r"D:\dsh workspace\dsh test project\assets\bodies"
os.makedirs(out_dir, exist_ok=True)

def white_key(img_rgb):
    """Alpha = distance to white, ramped."""
    arr = np.array(img_rgb).astype(np.float32)
    d = 255 - arr.mean(axis=2)  # 0 at white, high at dark
    alpha = np.clip((d - 8) / 40, 0, 1)
    return (alpha * 255).astype(np.uint8)

def crop_bbox(rgba, pad=4):
    a = np.array(rgba)
    mask = a[..., 3] > 16
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return rgba
    x0, x1 = max(0, xs.min()-pad), min(a.shape[1], xs.max()+1+pad)
    y0, y1 = max(0, ys.min()-pad), min(a.shape[0], ys.max()+1+pad)
    return rgba.crop((x0, y0, x1, y1))

# ---- Gorilla ----
gk = Image.open(os.path.join(src_dir, "300px-Donkey_Kong.png")).convert("RGB")
a = white_key(gk)
# feather
am = Image.fromarray(a).filter(ImageFilter.GaussianBlur(1.2))
rgba = Image.fromarray(np.dstack([np.array(gk), np.array(am)]), "RGBA")
rgba = crop_bbox(rgba)
rgba.save(os.path.join(out_dir, "gorilla_full.png"))
print("gorilla_full:", rgba.size)

# ---- Cockroach ----
ck = Image.open(os.path.join(src_dir,
    "ready-scared-cockroach-icon-cartoon-vector-insect-bug-ready-scared-cockroach-icon-cartoon-vector-insect-bug-dead-creepy-306345150.webp")).convert("RGB")
# inspect corners to decide keying
arr = np.array(ck)
corners = [arr[:20,:20], arr[:20,-20:], arr[-20:,:20], arr[-20:,-20:]]
print("cockroach corner means:", [c.reshape(-1,3).mean(0).round(1) for c in corners])
# save original for inspection
ck.save(os.path.join(out_dir, "cockroach_orig.png"))
print("cockroach size:", ck.size)
