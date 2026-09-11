"""v3: aggressive dilation to close all gaps in the hand-drawn contour,
then flood-fill. Also try morphological closing (dilate then erode) to
preserve the shape while closing gaps."""
import os
import numpy as np
from PIL import Image, ImageFilter
from collections import deque

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = Image.open(marked_path).convert("RGB")
arr = np.array(img, dtype=np.int16)
H, W = arr.shape[:2]

# Moderate thresholds
red_mask = (arr[:, :, 0] > 130) & (arr[:, :, 1] < 110) & (arr[:, :, 2] < 110)
blue_mask = (arr[:, :, 2] > 120) & (arr[:, :, 0] < 130) & (arr[:, :, 1] < 130)

def fill_with_dilation(line_mask, name, dilate_px):
    line_img = Image.fromarray((line_mask * 255).astype(np.uint8), "L")
    # Aggressive dilation
    for _ in range(dilate_px):
        line_img = line_img.filter(ImageFilter.MaxFilter(3))
    line = np.array(line_img) > 127
    print(f"{name}: dilate={dilate_px} line={line.sum()} px")

    exterior = np.zeros((H, W), dtype=bool)
    q = deque()
    def seed(y, x):
        if not line[y, x] and not exterior[y, x]:
            exterior[y, x] = True; q.append((y, x))
    for x in range(W):
        seed(0, x); seed(H - 1, x)
    for y in range(H):
        seed(y, 0); seed(y, W - 1)
    while q:
        y, x = q.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not line[ny, nx] and not exterior[ny, nx]:
                exterior[ny, nx] = True; q.append((ny, nx))

    filled = ~exterior
    ys, xs = np.nonzero(filled)
    if len(xs) == 0:
        print(f"{name}: empty"); return
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w, h = x1 - x0, y1 - y0
    # Check if the fill is reasonable (not too large, not scattered)
    bbox_area = w * h
    fill_ratio = len(xs) / bbox_area
    print(f"{name}: filled {len(xs)} px, bbox {w}x{h}={bbox_area}, ratio={fill_ratio:.2f}")
    if fill_ratio < 0.3 or bbox_area > 500 * 600:
        print(f"  -> fill looks wrong (ratio too low or bbox too large), skipping")
        return

    mask_img = Image.fromarray((filled * 255).astype(np.uint8), "L")
    margin = 5
    cx0 = max(0, x0 - margin); cy0 = max(0, y0 - margin)
    cx1 = min(W, x1 + margin); cy1 = min(H, y1 + margin)
    cropped = mask_img.crop((cx0, cy0, cx1, cy1))
    cropped.save(os.path.join(WS, "assets", "contours", f"filled_{name}.png"))
    print(f"  saved filled_{name}.png ({cropped.size[0]}x{cropped.size[1]})")

    # Debug overlay
    ov = Image.open(marked_path).convert("RGB")
    ov_arr = np.array(ov)
    ov_arr[filled] = [255, 160, 0]
    Image.fromarray(ov_arr).save(os.path.join(WS, "assets", "preview", f"fillcheck_{name}.png"))

# Try increasing dilation levels
for d in [5, 8, 12]:
    fill_with_dilation(red_mask, f"left_d{d}", d)
    fill_with_dilation(blue_mask, f"right_d{d}", d)

print("done")
