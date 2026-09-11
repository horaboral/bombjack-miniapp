"""Find which 400x400 region of the 800x800 raw matches the saved face crops."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
raw = np.array(Image.open(os.path.join(WS, "assets/raw/raw_f001.png")).convert("RGB"), dtype=np.int16)
left = np.array(Image.open(os.path.join(WS, "assets/faces/left/f_001.png")).convert("RGB"), dtype=np.int16)
right = np.array(Image.open(os.path.join(WS, "assets/faces/right/f_001.png")).convert("RGB"), dtype=np.int16)

H, W = raw.shape[:2]
best = {}
for name, crop in [("left", left), ("right", right)]:
    bd = 1e18; bx = by = 0
    for y in range(0, H - 400 + 1, 20):
        for x in range(0, W - 400 + 1, 20):
            region = raw[y:y+400, x:x+400]
            d = np.mean(np.abs(region - crop))
            if d < bd:
                bd = d; bx, by = x, y
    # refine
    for y in range(max(0, by - 20), min(H - 400, by + 21)):
        for x in range(max(0, bx - 20), min(W - 400, bx + 21)):
            region = raw[y:y+400, x:x+400]
            d = np.mean(np.abs(region - crop))
            if d < bd:
                bd = d; bx, by = x, y
    best[name] = (bx, by, bd)
    print(f"{name}: crop origin in raw = ({bx},{by}), mean abs diff = {bd:.2f}")
