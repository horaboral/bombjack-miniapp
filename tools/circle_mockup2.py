"""Circle-mask mockup v2: tighter face circle, positioned on each body's
actual head. CORRECTED mapping:
  left face (laughing)  -> cockroach body
  right face (talking)  -> gorilla body
The face circle diameter ~ 45% of body width, centered on the head zone."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
faces = os.path.join(WS, "assets", "faces")
bodies = os.path.join(WS, "assets", "bodies")
out = os.path.join(WS, "assets", "preview")
os.makedirs(out, exist_ok=True)

def circle_mask(size, radius_frac=0.5, feather=5):
    w, h = size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    r = int(max(w, h) * radius_frac)
    d.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))

def clear_head(body, head_rect, blur=12):
    x0, y0, x1, y1 = head_rect
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zone[y0:y1, x0:x1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

def build(face_name, body_path, face_center, face_d, tag, frame):
    body = Image.open(body_path).convert("RGBA")
    # clear the head region (a box around face_center, slightly larger than face)
    hd = int(face_d * 1.15)
    hx0 = face_center[0] - hd // 2; hy0 = face_center[1] - hd // 2
    hx1 = face_center[0] + hd // 2; hy1 = face_center[1] + hd // 2
    body = clear_head(body, (hx0, hy0, hx1, hy1))
    # face
    face = Image.open(os.path.join(faces, face_name, f"f_{frame:03d}.png")).convert("RGB")
    face = face.resize((face_d, face_d), Image.LANCZOS)
    face.putalpha(circle_mask(face.size))
    body.alpha_composite(face, (face_center[0] - face_d // 2, face_center[1] - face_d // 2))
    bg = Image.new("RGBA", body.size, (90, 90, 100, 255))
    bg.alpha_composite(body)
    bg.convert("RGB").save(os.path.join(out, f"mockup2_{tag}_f{frame}.jpg"), quality=90)
    print("saved", tag, bg.size, "face_d", face_d, "center", face_center)

# Cockroach: 358x734. Head (eyes+mouth) center ~ (179, 150), face_d ~ 160
build("left", os.path.join(bodies, "cockroach_full.png"), (179, 155), 165, "roach", 1)
# Gorilla: 300x232. Head (blue face) center ~ (150, 62), face_d ~ 88
build("right", os.path.join(bodies, "gorilla_full.png"), (150, 64), 90, "gorilla", 1)
print("done")
