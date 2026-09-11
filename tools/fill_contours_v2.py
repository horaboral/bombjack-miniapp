"""v2: extract user-drawn contours, DILATE to close gaps, then flood-fill
the interior. The line is hand-drawn and has breaks; dilation closes them
so the flood fill cannot leak."""
import os
import numpy as np
from PIL import Image, ImageFilter
from collections import deque

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = Image.open(marked_path).convert("RGB")
arr = np.array(img, dtype=np.int16)
H, W = arr.shape[:2]

# Contour lines (looser thresholds for hand-drawn anti-aliased lines)
red_mask = (arr[:, :, 0] > 120) & (arr[:, :, 0] - arr[:, :, 1] > 40) & (arr[:, :, 0] - arr[:, :, 2] > 40)
blue_mask = (arr[:, :, 2] > 100) & (arr[:, :, 2] - arr[:, :, 0] > 30) & (arr[:, :, 2] - arr[:, :, 1] > 20)

def fill_contour(line_mask, name, dilate=3):
    line_img = Image.fromarray((line_mask * 255).astype(np.uint8), "L")
    # Dilate the line to close gaps
    line_img = line_img.filter(ImageFilter.MaxFilter(dilate * 2 + 1))
    line = np.array(line_img) > 127
    print(f"{name}: line after dilation = {line.sum()} px")

    # Flood fill exterior from border
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
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not line[ny, nx] and not exterior[ny, nx]:
                exterior[ny, nx] = True; q.append((ny, nx))

    filled = ~exterior
    ys, xs = np.nonzero(filled)
    if len(xs) == 0:
        print(f"{name}: empty"); return
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    print(f"{name}: filled {len(xs)} px, bbox x=[{x0},{x1}] y=[{y0},{y1}] w={x1-x0} h={y1-y0}")

    mask_img = Image.fromarray((filled * 255).astype(np.uint8), "L")
    # Save full-size and cropped
    mask_img.save(os.path.join(WS, "assets", "contours", f"filled_{name}_full.png"))
    margin = 5
    cx0 = max(0, x0 - margin); cy0 = max(0, y0 - margin)
    cx1 = min(W, x1 + margin); cy1 = min(H, y1 + margin)
    cropped = mask_img.crop((cx0, cy0, cx1, cy1))
    cropped.save(os.path.join(WS, "assets", "contours", f"filled_{name}.png"))
    print(f"  saved filled_{name}.png ({cropped.size[0]}x{cropped.size[1]})")

    # Debug overlay: body-colored fill on the marked image
    ov = Image.open(marked_path).convert("RGB")
    ov_arr = np.array(ov)
    ov_arr[filled] = [255, 160, 0]
    Image.fromarray(ov_arr).save(os.path.join(WS, "assets", "preview", f"fillcheck_{name}.png"))

fill_contour(red_mask, "left", dilate=4)
fill_contour(blue_mask, "right", dilate=4)
print("done")
