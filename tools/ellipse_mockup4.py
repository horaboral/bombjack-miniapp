"""Ellipse mockup v4b: canvas compositing with correctly sized alpha.
CORRECTED mapping:
  left face (laughing)  -> cockroach body
  right face (talking)  -> gorilla body
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
faces = os.path.join(WS, "assets", "faces")
bodies = os.path.join(WS, "assets", "bodies")
out = os.path.join(WS, "assets", "preview")
os.makedirs(out, exist_ok=True)

def clear_zone(body, box, blur=12):
    x0, y0, x1, y1 = box
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zone[y0:y1, x0:x1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

def build(face_name, body_path, center, ew, eh, face_scale, face_off, tag, frame):
    body = Image.open(body_path).convert("RGBA")
    mx, my = int(ew * 0.22), int(eh * 0.22)
    cw, ch = ew + 2 * mx, eh + 2 * my
    body = clear_zone(body, (center[0] - cw // 2, center[1] - ch // 2,
                             center[0] + cw // 2, center[1] + ch // 2))
    # canvas
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    face = Image.open(os.path.join(faces, face_name, f"f_{frame:03d}.png")).convert("RGB")
    fs = int(400 * face_scale)
    face = face.resize((fs, fs), Image.LANCZOS).convert("RGBA")
    # paste face onto canvas at face_off (clipped to canvas bounds)
    canvas.alpha_composite(face, face_off)
    # now apply the ellipse alpha to the WHOLE canvas
    m = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([mx, my, mx + ew, my + eh], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(5))
    canvas.putalpha(m)
    body.alpha_composite(canvas, (center[0] - cw // 2, center[1] - ch // 2))
    bg = Image.new("RGBA", body.size, (90, 90, 100, 255))
    bg.alpha_composite(body)
    bg.convert("RGB").save(os.path.join(out, f"mockup4_{tag}_f{frame}.jpg"), quality=90)
    print("saved", tag, "ellipse", ew, "x", eh, "center", center,
          "face_scale", face_scale, "off", face_off)

# ---- Cockroach (358x734) ----
# face tilted CCW, mouth at lower-left of the 400x400 crop (~x120,y300).
# ellipse 196x246, face 0.60*400=240; place face so its lower-left (mouth)
# lands inside the ellipse center.
build("left", os.path.join(bodies, "cockroach_full.png"),
      (179, 186), 196, 246, 0.60, (22, 52), "roach", 1)

# ---- Gorilla (300x232): smaller, face 0.20*400=80 ----
build("right", os.path.join(bodies, "gorilla_full.png"),
      (150, 60), 58, 72, 0.20, (8, 14), "gorilla", 1)
print("done")
