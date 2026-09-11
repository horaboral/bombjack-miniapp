"""Crop the two faces from all 54 frames.
Boxes are manually tuned from visual inspection of the 800x800 frames:
  LEFT  face (laughing, sunglasses on head):  x 40..400, y 150..700
  RIGHT face (talking, sunglasses on head):   x 420..800, y 170..720
Output: square crops (400x400), center-aligned, for both characters.
Also save a 6x4 contact sheet per character for verification."""
import os
from PIL import Image

src_dir = r"D:\dsh workspace\dsh test project\assets\face_frames"
out_dir = r"D:\dsh workspace\dsh test project\assets"
os.makedirs(os.path.join(out_dir, "faces"), exist_ok=True)

frames = sorted(f for f in os.listdir(src_dir) if f.startswith("frame_") and f.endswith(".png"))
N = len(frames)
print(f"{N} frames")

# (name, left, upper, right, lower, crop_size)
BOXES = [
    ("left",  40, 150, 400, 700, 400),
    ("right", 420, 170, 800, 720, 400),
]

for name, x0, y0, x1, y1, size in BOXES:
    out = os.path.join(out_dir, "faces", f"{name}")
    os.makedirs(out, exist_ok=True)
    crops = []
    for i, f in enumerate(frames):
        im = Image.open(os.path.join(src_dir, f)).convert("RGB")
        c = im.crop((x0, y0, x1, y1))
        # make square
        cw, ch = c.size
        s = min(cw, ch)
        off = ((cw - s)//2, (ch - s)//2)
        c = c.crop((off[0], off[1], off[0]+s, off[1]+s))
        c = c.resize((size, size), Image.LANCZOS)
        c.save(os.path.join(out, f"f_{i:03d}.png"))
        crops.append(c)
    print(f"{name}: saved {len(crops)} crops of {size}x{size}")
    # contact sheet 9x6
    cols, rows = 9, 6
    sheet = Image.new("RGB", (cols*size//3, rows*size//3))
    for i, c in enumerate(crops[:cols*rows]):
        r, cc = divmod(i, cols)
        sheet.paste(c.resize((size//3, size//3)), (cc*size//3, r*size//3))
    sheet.save(os.path.join(out_dir, f"faces_{name}_sheet.jpg"), quality=80)
    print(f"{name}: contact sheet saved")
