"""Extract the user-drawn face contours (red=left, blue=right) from
'faces marked raw_f001.jpg' as binary masks. Save as PNG masks and
report their bounding boxes."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = Image.open(marked_path).convert("RGB")
arr = np.array(img, dtype=np.int16)

# Red contour: high R, low G, low B
red_mask = (arr[:, :, 0] > 140) & (arr[:, :, 1] < 110) & (arr[:, :, 2] < 110)
# Blue contour: high B, low R, low G
blue_mask = (arr[:, :, 2] > 120) & (arr[:, :, 0] < 130) & (arr[:, :, 1] < 130)

for name, mask in [("left", red_mask), ("right", blue_mask)]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        print(f"{name}: no pixels found")
        continue
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    print(f"{name}: {len(xs)} px, bbox x=[{x0},{x1}] y=[{y0},{y1}] w={w} h={h} center=({cx:.0f},{cy:.0f})")
    # Save the contour mask (full 800x800) and a cropped version
    mask_img = Image.fromarray((mask * 255).astype(np.uint8), "L")
    mask_img.save(os.path.join(WS, "assets", "contours", f"contour_{name}_full.png"))
    # Crop to bbox with small margin
    margin = 10
    cx0 = max(0, x0 - margin); cy0 = max(0, y0 - margin)
    cx1 = min(arr.shape[1], x1 + margin); cy1 = min(arr.shape[0], y1 + margin)
    cropped = mask_img.crop((cx0, cy0, cx1, cy1))
    cropped.save(os.path.join(WS, "assets", "contours", f"contour_{name}.png"))
    print(f"  saved contour_{name}.png ({cropped.size[0]}x{cropped.size[1]})")

print("done")
