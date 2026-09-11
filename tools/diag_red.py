"""Diagnose the red contour: sample pixel values along the hand-drawn line
and compare to skin tones to find a strict threshold."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = Image.open(marked_path).convert("RGB")
arr = np.array(img, dtype=np.int16)

# The red line is hand-drawn, pure red. Sample a few known points on the line.
# From the marked image, the red line goes around the left face.
# Let's sample pixels that are clearly "red line" vs "skin".
# Red line should have: R high, G very low, B very low (like 200, 30, 30)
# Skin should have: R high, G medium, B medium (like 200, 150, 130)

# Strict red: R > 150, G < 80, B < 80, and R - G > 80, R - B > 80
strict_red = (arr[:, :, 0] > 150) & (arr[:, :, 1] < 80) & (arr[:, :, 2] < 80)
ys, xs = np.nonzero(strict_red)
print(f"strict red: {len(xs)} px")
if len(xs):
    print(f"  bbox x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}]")
    # Sample some values
    for i in range(0, len(xs), max(1, len(xs) // 10)):
        y, x = ys[i], xs[i]
        print(f"  ({x},{y}): RGB=({arr[y,x,0]},{arr[y,x,1]},{arr[y,x,2]})")

# Also try: R > 180, G < 60, B < 60
very_strict = (arr[:, :, 0] > 180) & (arr[:, :, 1] < 60) & (arr[:, :, 2] < 60)
ys2, xs2 = np.nonzero(very_strict)
print(f"\nvery strict red: {len(xs2)} px")
if len(xs2):
    print(f"  bbox x=[{xs2.min()},{xs2.max()}] y=[{ys2.min()},{ys2.max()}]")

# Blue line: should be pure blue. B high, R low, G low
strict_blue = (arr[:, :, 2] > 150) & (arr[:, :, 0] < 80) & (arr[:, :, 1] < 100)
ys3, xs3 = np.nonzero(strict_blue)
print(f"\nstrict blue: {len(xs3)} px")
if len(xs3):
    print(f"  bbox x=[{xs3.min()},{xs3.max()}] y=[{ys3.min()},{ys3.max()}]")
    for i in range(0, len(xs3), max(1, len(xs3) // 10)):
        y, x = ys3[i], xs3[i]
        print(f"  ({x},{y}): RGB=({arr[y,x,0]},{arr[y,x,1]},{arr[y,x,2]})")

print("done")
