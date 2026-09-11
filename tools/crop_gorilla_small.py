"""Tightly crop the small gorilla frames to the opaque body bbox,
so the game can draw frame size == body size with no transparent padding."""
from PIL import Image
import numpy as np
import os

SRC = r"D:\dsh workspace\dsh test project\assets\final_small\gorilla"
# Target body display: 54 wide x 65 tall (aspect 0.824, 35% bigger than 40x49... check:
# v30 body drawn 40x49 (aspect 0.816). 35% bigger keeping proportions: 40*1.35=54, 49*1.35=66.15->66)
TW, TH = 54, 66
for f in sorted(os.listdir(SRC)):
    if not f.endswith(".png"):
        continue
    p = os.path.join(SRC, f)
    im = Image.open(p).convert("RGBA")
    a = np.array(im.getchannel("A"))
    opaque = a > 8
    ys, xs = np.where(opaque)
    if len(xs) == 0:
        continue
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    # pad 2px so anti-aliased edges aren't clipped
    pad = 2
    box = (max(0, box[0]-pad), max(0, box[1]-pad),
           min(im.size[0], box[2]+pad), min(im.size[1], box[3]+pad))
    im = im.crop(box)
    im = im.resize((TW, TH), Image.LANCZOS)
    im.save(p, optimize=True)
print(f"cropped+resized {TW}x{TH}")
