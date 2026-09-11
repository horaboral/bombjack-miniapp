"""Composite grabcut test frames over a checkerboard."""
import os
from PIL import Image

out = r"D:\dsh workspace\dsh test project\assets\faces_alpha"
def checker(w, h, sq=40):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            c = (x // sq + y // sq) % 2
            px[x, y] = (200, 200, 200) if c else (40, 40, 40)
    return img

for name in ("left", "right"):
    for i in (0, 27, 53):
        fg = Image.open(os.path.join(out, f"{name}_{i:03d}_gc.png")).convert("RGBA")
        bg = checker(fg.width, fg.height)
        comp = Image.alpha_composite(bg.convert("RGBA"), fg).convert("RGB")
        comp.save(os.path.join(out, f"{name}_{i:03d}_gc_check.jpg"), quality=85)
print("gc previews done")
