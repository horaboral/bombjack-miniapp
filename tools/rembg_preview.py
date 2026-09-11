"""Checkerboard preview of rembg mattes."""
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
    fg = Image.open(os.path.join(out, f"{name}_027_rembg.png")).convert("RGBA")
    bg = checker(fg.width, fg.height)
    comp = Image.alpha_composite(bg.convert("RGBA"), fg).convert("RGB")
    comp.save(os.path.join(out, f"{name}_027_rembg_check.jpg"), quality=88)
print("rembg previews done")
