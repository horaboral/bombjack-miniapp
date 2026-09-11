"""Texture-based face segmentation.

The wall is smooth (low local gradient magnitude); the face (skin, hair,
beard, features) has high local detail. Combine gradient energy with a
flood-fill from borders to get a clean face mask. Works per-frame even when
skin color ~= wall color."""
import os
import numpy as np
import cv2
from PIL import Image, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
loose = os.path.join(WS, "assets", "faces")
out = os.path.join(WS, "assets", "faces_alpha")
os.makedirs(out, exist_ok=True)

def segment(arr):
    h, w = arr.shape[:2]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    # Sobel gradient magnitude
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx**2 + gy**2)
    # blur to local energy (16px window)
    energy = cv2.blur(grad, (15, 15))
    # threshold: high energy = detail = face
    e_min, e_max = float(energy.min()), float(energy.max())
    norm = (energy - e_min) / max(1e-6, (e_max - e_min))
    T = 0.30
    detail = (norm > T).astype(np.uint8)
    # close gaps so the face is one solid blob
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    detail = cv2.morphologyEx(detail, cv2.MORPH_CLOSE, k, iterations=3)
    detail = cv2.dilate(detail, k, iterations=2)
    # keep only the largest connected component (the face)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(detail, 8)
    if n <= 1:
        return None
    # largest by area (excluding background label 0)
    areas = stats[1:, cv2.CC_STAT_AREA]
    best = 1 + int(np.argmax(areas))
    mask = (labels == best).astype(np.uint8)
    # feather
    m = Image.fromarray((mask * 255))
    m = m.filter(ImageFilter.GaussianBlur(2.5))
    return Image.fromarray(np.dstack([arr, np.array(m)]), "RGBA")

for name in ("left", "right"):
    ok = 0
    for i in range(1, 54):
        im = Image.open(os.path.join(loose, name, f"f_{i:03d}.png")).convert("RGB")
        res = segment(np.array(im))
        if res is None:
            continue
        res.save(os.path.join(out, f"{name}_{i:03d}_tex.png"))
        ok += 1
    print(name, "texture-segmented", ok, "frames")
print("done")
