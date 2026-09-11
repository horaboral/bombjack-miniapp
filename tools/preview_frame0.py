"""Frame-0 face-replacement preview.
- Matting: GrabCut on the 400x400 face crop (5 iters), then enforce a hand-drawn
  oval boundary curve so no ragged islands survive: anything outside the oval
  is forced to background.
- Bodies: gorilla / cockroach with their own head region cleared, animated face
  composited over the head zone.
Output: two ~500px-tall PNGs (one per character) for user review.
"""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
faces_dir = os.path.join(WS, "assets", "faces")
bodies_dir = os.path.join(WS, "assets", "bodies")
out_dir = os.path.join(WS, "assets", "preview")
os.makedirs(out_dir, exist_ok=True)

def matting_face(crop_path):
    arr = np.array(Image.open(crop_path).convert("RGB"))
    h, w = arr.shape[:2]
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    # GrabCut rect: face is centered, leave 12% margins as probable bg
    mx, my = int(w * 0.12), int(h * 0.10)
    rect = (mx, my, w - 2 * mx, h - 2 * my)
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    # Enforce boundary: hand-drawn oval (the "curve line" the user asked for).
    oval = np.zeros((h, w), np.uint8)
    cv2.ellipse(oval, (w // 2, int(h * 0.52)), (int(w * 0.42), int(h * 0.47)), 0, 0, 360, 255, -1)
    fg = cv2.bitwise_and(fg, oval)
    # Close small holes, then feather
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k, iterations=2)
    m = Image.fromarray(fg).filter(ImageFilter.GaussianBlur(1.8))
    return Image.fromarray(np.dstack([arr, np.array(m)]), "RGBA")

def clear_body_head(body_path, head_rect):
    body = Image.open(body_path).convert("RGBA")
    x0, y0, x1, y1 = head_rect
    # feathered mask over the head zone, erase alpha there
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zone[y0:y1, x0:x1] = 255
    zm = Image.fromarray(zone).filter(ImageFilter.GaussianBlur(8))
    za = np.array(zm).astype(np.float32) / 255.0
    a[..., 3] = (a[..., 3] * (1 - za)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

def build(char, body_path, head_rect, face_i):
    body = clear_body_head(body_path, head_rect)
    face = matting_face(os.path.join(faces_dir, char, f"f_{face_i:03d}.png"))
    # scale face to ~78% of body width, center on head zone
    fw = int(body.width * 0.80)
    face_r = face.resize((fw, fw), Image.LANCZOS)
    hx = (head_rect[0] + head_rect[2]) // 2
    hy = (head_rect[1] + head_rect[3]) // 2
    body.alpha_composite(face_r, (hx - fw // 2, hy - fw // 2))
    # put on a mid-gray bg for review
    bg = Image.new("RGBA", body.size, (90, 90, 100, 255))
    bg.alpha_composite(body)
    return bg.convert("RGB")

gorilla_body = os.path.join(bodies_dir, "gorilla_full.png")
cockroach_body = os.path.join(bodies_dir, "cockroach_full.png")

gw, gh = Image.open(gorilla_body).size
# gorilla head: blue face + hair top (tighter than before)
gor_head = (int(gw*0.30), int(gh*0.04), int(gw*0.70), int(gh*0.44))
cw, ch = Image.open(cockroach_body).size
# cockroach head: eyes + mouth + antennae base
ckr_head = (int(cw*0.24), int(ch*0.03), int(cw*0.76), int(ch*0.38))

p1 = build("left", gorilla_body, gor_head, 0)
p1.save(os.path.join(out_dir, "preview_gorilla_f0.jpg"), quality=90)
p2 = build("right", cockroach_body, ckr_head, 0)
p2.save(os.path.join(out_dir, "preview_cockroach_f0.jpg"), quality=90)
print("previews saved:", p1.size, p2.size)
