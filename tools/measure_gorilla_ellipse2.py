"""Measure the white ellipse using the largest connected white component
to exclude watermark text and other white pixels."""
import numpy as np
import cv2
from PIL import Image

DST = r"D:\dsh workspace\dsh test project\assets\bodies\gorilla_headless_new.jpg"
img = cv2.imread(DST)
arr = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.int16)
H, W = arr.shape[:2]

# White mask
white = (arr.min(axis=2) > 235).astype(np.uint8)
print(f"total white px: {white.sum()}")

# Find connected components, keep the largest
n, labels, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=8)
# stats: [x, y, w, h, area] for each component (0 = background)
areas = stats[1:, cv2.CC_STAT_AREA]  # skip background
largest_idx = 1 + np.argmax(areas)
x, y, w, h, area = stats[largest_idx]
cx, cy = x + w / 2, y + h / 2
rx, ry = w / 2, h / 2
print(f"largest white component: bbox=({x},{y},{w},{h}) area={area}")
print(f"center=({cx:.1f},{cy:.1f})  rx={rx:.1f} ry={ry:.1f}")
print(f"fill ratio: {area/(w*h):.3f}")

# Save the mask for compositing
mask = (labels == largest_idx).astype(np.uint8) * 255
# Crop to bbox with margin
margin = 5
cx0 = max(0, x - margin); cy0 = max(0, y - margin)
cx1 = min(W, x + w + margin); cy1 = min(H, y + h + margin)
cv2.imwrite(r"D:\dsh workspace\dsh test project\assets\contours\gorilla_white_ellipse.png",
            mask[cy0:cy1, cx0:cx1])
print(f"saved mask crop ({cx1-cx0}x{cy1-cy0})")
