"""Checkerboard preview of MODNet mattes."""
import os
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
out = os.path.join(WS, "assets", "faces_alpha")

def checker(w, h, sq=40):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            c = (x // sq + y // sq) % 2
            px[x, y] = (200, 200, 200) if c else (40, 40, 40)
    return img

for name in ("left", "right"):
    for i in (1, 27, 53):
        fg = Image.open(os.path.join(out, f"{name}_{i:03d}_modnet.png")).convert("RGBA")
        bg = checker(fg.width, fg.height)
        comp = Image.alpha_composite(bg.convert("RGBA"), fg).convert("RGB")
        comp.save(os.path.join(out, f"{name}_{i:03d}_modnet_check.jpg"), quality=88)
print("modnet previews done")
