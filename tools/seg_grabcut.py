"""Segment faces using OpenCV GrabCut with a rectangular foreground hint.

GrabCut is iterative and uses texture + color + spatial priors, which
handles the skin-vs-yellow-wall ambiguity much better than raw color
distance. We seed it with a rectangle that covers the face (inner 80% of
the crop, leaving the corners as probable background)."""
import os
import cv2
import numpy as np
from PIL import Image, ImageFilter

src = r"D:\dsh workspace\dsh test project\assets\faces"
out = r"D:\dsh workspace\dsh test project\assets\faces_alpha"
os.makedirs(out, exist_ok=True)

def segment_grabcut(arr, n_iter=5):
    h, w = arr.shape[:2]
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    # Rectangle: inner 78% of the crop (face is centered, wall at corners)
    margin_x = int(w * 0.11)
    margin_y = int(h * 0.11)
    rect = (margin_x, margin_y, w - 2*margin_x, h - 2*margin_y)
    mask = np.zeros((h, w), np.uint8)
    # Initial mask: inside rect = probable FG, outside = probable BG
    mask[:] = cv2.GC_BGD
    mask[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]] = cv2.GC_PR_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, bgd, fgd, n_iter, cv2.GC_INIT_WITH_RECT)
    # FG where mask is GC_FGD or GC_PR_FGD
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # Feather
    m = Image.fromarray(fg)
    m = m.filter(ImageFilter.GaussianBlur(2))
    return Image.fromarray(np.dstack([arr, np.array(m)]), "RGBA")

for name in ("left", "right"):
    for i in (0, 27, 53):
        im = Image.open(os.path.join(src, name, f"f_{i:03d}.png")).convert("RGB")
        res = segment_grabcut(np.array(im))
        res.save(os.path.join(out, f"{name}_{i:03d}_gc.png"))
    print(name, "grabcut test done")
print("done")
