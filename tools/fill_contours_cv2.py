"""v2: looser threshold + larger closing kernel to connect fragmented
hand-drawn line."""
import os
import numpy as np
import cv2
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = cv2.imread(marked_path)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
arr = img.astype(np.int16)

# Looser thresholds to catch more of the anti-aliased hand-drawn line
# Red: R > 120, R - G > 30, R - B > 30
red_mask = ((arr[:, :, 0] > 120) & (arr[:, :, 0] - arr[:, :, 1] > 30) & (arr[:, :, 0] - arr[:, :, 2] > 30)).astype(np.uint8) * 255
# Blue: B > 100, B - R > 20, B - G > 10
blue_mask = ((arr[:, :, 2] > 100) & (arr[:, :, 2] - arr[:, :, 0] > 20) & (arr[:, :, 2] - arr[:, :, 1] > 10)).astype(np.uint8) * 255

def fill_contour_cv(mask, name, kernel_size=31):
    print(f"{name}: raw line = {(mask > 127).sum()} px")
    # Large morphological closing to connect fragments
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    print(f"  after closing (k={kernel_size}): {(closed > 127).sum()} px")

    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filter by area
    valid = [c for c in contours if cv2.contourArea(c) > 2000]
    print(f"  found {len(contours)} contours, {len(valid)} valid (area>2000)")
    if not valid:
        print("  -> no valid contours")
        return

    # Fill all valid contours (there might be multiple fragments)
    filled = np.zeros_like(mask)
    for c in valid:
        cv2.drawContours(filled, [c], -1, 255, -1)
    total_area = (filled > 127).sum()
    print(f"  total filled: {total_area} px")

    if total_area < 5000:
        print("  -> total fill too small, skipping")
        return

    ys, xs = np.nonzero(filled > 127)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    print(f"  bbox: x=[{x0},{x1}] y=[{y0},{y1}] w={x1-x0} h={y1-y0}")

    mask_img = Image.fromarray(filled, "L")
    margin = 5
    cx0 = max(0, x0 - margin); cy0 = max(0, y0 - margin)
    cx1 = min(arr.shape[1], x1 + margin); cy1 = min(arr.shape[0], y1 + margin)
    cropped = mask_img.crop((cx0, cy0, cx1, cy1))
    cropped.save(os.path.join(WS, "assets", "contours", f"filled_{name}.png"))
    print(f"  saved filled_{name}.png ({cropped.size[0]}x{cropped.size[1]})")

    # Debug overlay
    ov = img.copy()
    ov[filled > 127] = [255, 160, 0]
    cv2.imwrite(os.path.join(WS, "assets", "preview", f"fillcheck_{name}.png"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))

fill_contour_cv(red_mask, "left", kernel_size=41)
fill_contour_cv(blue_mask, "right", kernel_size=41)
print("done")
