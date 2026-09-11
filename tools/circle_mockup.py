"""Circle-mask face mockup (the 'curve line' approach), CORRECTED mapping:
  left face (laughing)  -> cockroach body
  right face (talking)  -> gorilla body
Each face gets a feathered circular alpha, composited over the headless body."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
faces = os.path.join(WS, "assets", "faces")
bodies = os.path.join(WS, "assets", "bodies")
out = os.path.join(WS, "assets", "preview")
os.makedirs(out, exist_ok=True)

def circle_mask(size, radius_frac=0.47, feather=6):
    w, h = size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    r = int(max(w, h) * radius_frac)
    d.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather))
    return m

def clear_head(body_path, head_rect, blur=10):
    body = Image.open(body_path).convert("RGBA")
    x0, y0, x1, y1 = head_rect
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zone[y0:y1, x0:x1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

def build(face_name, body_path, head_rect, frame, tag):
    body = clear_head(body_path, head_rect)
    face = Image.open(os.path.join(faces, face_name, f"f_{frame:03d}.png")).convert("RGB")
    # scale face so its circle ~ 85% of body width
    fw = int(body.width * 0.86)
    face = face.resize((fw, fw), Image.LANCZOS)
    face.putalpha(circle_mask(face.size))
    hx = (head_rect[0] + head_rect[2]) // 2
    hy = (head_rect[1] + head_rect[3]) // 2
    body.alpha_composite(face, (hx - fw // 2, hy - fw // 2))
    bg = Image.new("RGBA", body.size, (90, 90, 100, 255))
    bg.alpha_composite(body)
    bg.convert("RGB").save(os.path.join(out, f"mockup_{tag}_f{frame}.jpg"), quality=90)
    print("saved mockup", tag, bg.size)

gw, gh = Image.open(os.path.join(bodies, "gorilla_full.png")).size
gor_head = (int(gw * 0.30), int(gh * 0.02), int(gw * 0.70), int(gh * 0.46))
cw, ch = Image.open(os.path.join(bodies, "cockroach_full.png")).size
ckr_head = (int(cw * 0.22), int(ch * 0.03), int(cw * 0.78), int(ch * 0.36))

# CORRECTED mapping
build("left", os.path.join(bodies, "cockroach_full.png"), ckr_head, 1, "roach_leftface")
build("right", os.path.join(bodies, "gorilla_full.png"), gor_head, 1, "gorilla_rightface")
print("done")
