"""Ellipse-mask mockup v3:
- taller ellipse so the mouth/chin is fully inside (face crops are square,
  mouth sits low)
- body-proportional sizing: character total height ~ 1/8 of a 734px canvas
  is too small to judge, so sizes are set relative to each body
- tighter left/right margins: ellipse narrower than tall
CORRECTED mapping: left face (laughing) -> cockroach, right face (talking) -> gorilla.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
faces = os.path.join(WS, "assets", "faces")
bodies = os.path.join(WS, "assets", "bodies")
out = os.path.join(WS, "assets", "preview")
os.makedirs(out, exist_ok=True)

def ellipse_mask(w, h, rx, ry, feather=5):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([w // 2 - rx, h // 2 - ry, w // 2 + rx, h // 2 + ry], fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))

def clear_zone(body, box, blur=12):
    x0, y0, x1, y1 = box
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zone[y0:y1, x0:x1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

def build(face_name, body_path, center, ew, eh, tag, frame):
    body = Image.open(body_path).convert("RGBA")
    pad = int(ew * 0.18)
    body = clear_zone(body, (center[0] - ew // 2 - pad, center[1] - eh // 2 - pad,
                             center[0] + ew // 2 + pad, center[1] + eh // 2 + pad))
    # face canvas: ellipse w x h, face image scaled to cover the ellipse fully
    face = Image.open(os.path.join(faces, face_name, f"f_{frame:03d}.png")).convert("RGB")
    s = max(ew, eh)
    face = face.resize((s, s), Image.LANCZOS)
    # crop the square to the ellipse canvas (center crop)
    ox = (s - ew) // 2; oy = (s - eh) // 2
    face = face.crop((ox, oy, ox + ew, oy + eh))
    face.putalpha(ellipse_mask(ew, eh, ew // 2, eh // 2))
    body.alpha_composite(face, (center[0] - ew // 2, center[1] - eh // 2))
    bg = Image.new("RGBA", body.size, (90, 90, 100, 255))
    bg.alpha_composite(body)
    bg.convert("RGB").save(os.path.join(out, f"mockup3_{tag}_f{frame}.jpg"), quality=90)
    print("saved", tag, "ellipse", ew, "x", eh, "center", center)

# Cockroach 358x734: head zone ~ center (179,150); face ellipse wider than before
# but not full-width; mouth must be included -> taller ellipse
build("left", os.path.join(bodies, "cockroach_full.png"), (179, 168), 190, 230, "roach", 1)
# Gorilla 300x232: face smaller (body is short/wide), center on the head
build("right", os.path.join(bodies, "gorilla_full.png"), (150, 66), 78, 96, "gorilla", 1)
print("done")
