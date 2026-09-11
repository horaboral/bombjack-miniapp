"""Test rembg matting on one face crop per character."""
import os
from PIL import Image
from rembg import new_session, remove

WS = r"D:\dsh workspace\dsh test project"
out = os.path.join(WS, "assets", "faces_alpha")
os.makedirs(out, exist_ok=True)

session = new_session("isnet-general-use")  # strong general-purpose matte

for name in ("left", "right"):
    src = os.path.join(WS, "assets", "faces", name, "f_027.png")
    fg = remove(Image.open(src).convert("RGB"), session=session, alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=15,
                alpha_matting_erode_size=10)
    fg.save(os.path.join(out, f"{name}_027_rembg.png"))
    print(name, "rembg done", fg.size)
print("done")
