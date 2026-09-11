"""Key the cockroach, crop both, and build an annotated preview showing
where each body's head sits (for the face-replacement geometry)."""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

src_dir = r"C:\Users\gru\Pictures\loj shavale"
out_dir = r"D:\dsh workspace\dsh test project\assets\bodies"

def white_key(rgb, ramp_lo=8, ramp_hi=45):
    arr = np.array(rgb).astype(np.float32)
    d = 255 - arr.mean(axis=2)
    alpha = np.clip((d - ramp_lo) / (ramp_hi - ramp_lo), 0, 1)
    return (alpha * 255).astype(np.uint8)

def to_rgba(rgb):
    a = Image.fromarray(white_key(rgb)).filter(ImageFilter.GaussianBlur(1.0))
    return Image.fromarray(np.dstack([np.array(rgb), np.array(a)]), "RGBA")

def crop_bbox(rgba, pad=6):
    a = np.array(rgba)
    mask = a[..., 3] > 20
    ys, xs = np.where(mask)
    x0, x1 = max(0, xs.min()-pad), min(a.shape[1], xs.max()+1+pad)
    y0, y1 = max(0, ys.min()-pad), min(a.shape[0], ys.max()+1+pad)
    return rgba.crop((x0, y0, x1, y1))

gk = Image.open(os.path.join(src_dir, "300px-Donkey_Kong.png")).convert("RGB")
gor = crop_bbox(to_rgba(gk))
gor.save(os.path.join(out_dir, "gorilla_full.png"))

ck = Image.open(os.path.join(src_dir,
    "ready-scared-cockroach-icon-cartoon-vector-insect-bug-ready-scared-cockroach-icon-cartoon-vector-insect-bug-dead-creepy-306345150.webp")).convert("RGB")
ckr = crop_bbox(to_rgba(ck))
ckr.save(os.path.join(out_dir, "cockroach_full.png"))

print("gorilla:", gor.size, "cockroach:", ckr.size)

# ---- Annotated preview: draw head-region rectangles ----
def annotate(rgba, head_rect, label, path):
    bg = Image.new("RGBA", rgba.size, (60, 60, 70, 255))
    bg.alpha_composite(rgba)
    d = ImageDraw.Draw(bg)
    d.rectangle(head_rect, outline="red", width=4)
    d.text((8, 8), label, fill="red")
    bg.convert("RGB").save(path, quality=88)

# Gorilla head: from the image, head/face is roughly top-center.
gw, gh = gor.size
gor_head = (int(gw*0.28), int(gh*0.02), int(gw*0.72), int(gh*0.42))
annotate(gor, gor_head, "gorilla head zone", os.path.join(out_dir, "gorilla_annotated.jpg"))
# Cockroach head: top of the bug (head with eyes + antennae)
cw, ch = ckr.size
ckr_head = (int(cw*0.30), int(ch*0.02), int(cw*0.70), int(ch*0.40))
annotate(ckr, ckr_head, "cockroach head zone", os.path.join(out_dir, "cockroach_annotated.jpg"))
print("annotated previews saved")
