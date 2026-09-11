"""Check: within the white ellipse region on the composite, how many pixels
are face (bright) vs black (background showing through)?"""
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
comp = np.array(Image.open(f"{WS}/assets/final/gorilla/f_001.png").convert("RGB"))
# Body ellipse: center (388.5, 235.5), rx=81.5, ry=103.5
# Sample a grid of points inside the ellipse
g_cx, g_cy, g_rx, g_ry = 388.5, 235.5, 81.5, 103.5
face_px = 0
total_px = 0
dark_px = 0
for x in range(int(g_cx - g_rx), int(g_cx + g_rx) + 1):
    for y in range(int(g_cy - g_ry), int(g_cy + g_ry) + 1):
        if 0 <= x < comp.shape[1] and 0 <= y < comp.shape[0]:
            # Inside ellipse?
            dx = (x - g_cx) / g_rx
            dy = (y - g_cy) / g_ry
            if dx*dx + dy*dy <= 1.0:
                total_px += 1
                r, g, b = comp[y, x]
                brightness = (int(r) + int(g) + int(b)) / 3
                if brightness > 60:
                    face_px += 1
                else:
                    dark_px += 1
print(f"pixels in ellipse: {total_px}")
print(f"face/bright: {face_px} ({100*face_px/total_px:.1f}%)")
print(f"dark: {dark_px} ({100*dark_px/total_px:.1f}%)")
