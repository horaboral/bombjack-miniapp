"""Overlay the SAM mask on the raw frame (mask = red) so we can SEE where the
cut actually is relative to the real faces. One cell per frame."""
import os
import numpy as np
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
RD = os.path.join(WS, "llama-780m", "roach-debug")
RAW = os.path.join(WS, "assets", "raw")
COM = r"D:\ComfyUI-Container\workspace\output"

FRAMES = [("f001", "001"), ("f002", "002"), ("f027", "027")]
W, H = 800, 800

def cell(tag, idx):
    raw = Image.open(os.path.join(RAW, f"raw_{tag}.png")).convert("RGB")
    m = Image.open(os.path.join(COM, f"samtest_batch_{idx}_00001_.png")).convert("L")
    ma = (np.array(m) > 12)
    # red overlay where mask is on, green outline at the mask edge
    ov = raw.copy()
    a = np.array(ov)
    a[ma] = (a[ma]*0.45 + np.array([220, 30, 30])*0.55).astype(np.uint8)
    ov = Image.fromarray(a)
    # edge: mask minus eroded mask
    from scipy import ndimage
    edge = ma & ~ndimage.binary_erosion(ma, iterations=2)
    ea = np.array(ov); ea[edge] = (0, 230, 0)
    ov = Image.fromarray(ea)
    c = Image.new("RGB", (W, H + 34), (15, 15, 15))
    c.paste(ov, (0, 34))
    d = ImageDraw.Draw(c)
    d.text((6, 6), f"{tag}  (mask {idx})  red=inside cut, green=cut edge", fill=(255, 255, 0))
    return c

sheet = Image.new("RGB", (W*3 + 20, H + 34), (0, 0, 0))
for i, (tag, idx) in enumerate(FRAMES):
    sheet.paste(cell(tag, idx), (i*(W+10), 0))
sheet.save(os.path.join(RD, "mask_overlay.png"))
print("saved mask_overlay.png", sheet.size)
