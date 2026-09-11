"""Erase dark pixels in the head region of each headless body so the
body's dark outline/antennae don't peek through the face's transparent
regions. Paint dark pixels with the local background color (white)."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"

def erase_dark_in_region(body_path, out_path, y_range, x_range, dark_thresh=100):
    body = Image.open(body_path).convert("RGB")
    arr = np.array(body, dtype=np.int16)
    H, W = arr.shape[:2]

    y0, y1 = y_range
    x0, x1 = x_range
    region = arr[y0:y1, x0:x1, :]

    # Dark pixels: max channel < dark_thresh
    dark = region.max(axis=2) < dark_thresh
    print(f"  region y=[{y0},{y1}] x=[{x0},{x1}]: {dark.sum()} dark pixels")

    # Paint dark pixels white
    arr[y0:y1, x0:x1, :][dark] = [255, 255, 255]

    erased = Image.fromarray(arr.astype(np.uint8))
    erased.save(out_path, quality=95)
    print(f"  saved {out_path}")

# Roach: head area is upper center. The dark outline arcs from the antennae
# down around where the head was. Let's erase dark pixels in y=[40, 280], x=[220, 580]
print("Roach:")
erase_dark_in_region(
    os.path.join(WS, "assets", "bodies", "roach_headless.jpg"),
    os.path.join(WS, "assets", "bodies", "roach_headless_clean.jpg"),
    (40, 280), (220, 580), dark_thresh=100
)

# Gorilla: head area is upper center. Erase dark pixels in y=[0, 130], x=[40, 260]
print("Gorilla:")
erase_dark_in_region(
    os.path.join(WS, "assets", "bodies", "gorilla_headless.jpg"),
    os.path.join(WS, "assets", "bodies", "gorilla_headless_clean.jpg"),
    (0, 130), (40, 260), dark_thresh=80
)

print("done")
