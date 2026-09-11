"""Erase the roach body's dark head outline and antennae by painting
dark pixels in the head region white (matching the background).
The head region is the upper portion of the body, above the brown collar."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
body_path = os.path.join(WS, "assets", "bodies", "roach_headless.jpg")
body = Image.open(body_path).convert("RGB")
arr = np.array(body, dtype=np.int16)
H, W = arr.shape[:2]

# The head region: upper portion, above the brown collar.
# The brown collar starts around y=200 (from visual inspection).
# The head area is roughly y=0 to y=250, x=250 to x=550.
# But the antennae extend up to y=40, and the dark outline arcs
# around the head area.

# Strategy: in the head region (y < 280), paint any pixel that is
# "dark" (all channels < 80) to white (255,255,255).
# This will erase the dark outline and antennae.

head_region = arr[:280, :, :]
# Dark pixels: all channels < 80
dark = head_region.max(axis=2) < 80
print(f"Dark pixels in head region (y<280): {dark.sum()}")

# Paint dark pixels white
arr[:280, :, :][dark] = [255, 255, 255]

# Save the erased body
erased = Image.fromarray(arr.astype(np.uint8))
erased_path = os.path.join(WS, "assets", "bodies", "roach_headless_erased.jpg")
erased.save(erased_path, quality=95)
print(f"Saved erased body: {erased_path}")

# Also save a preview with the face composited (using v22 approach)
print("done")
