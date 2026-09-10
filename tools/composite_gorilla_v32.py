"""v32: asymmetric ellipse — left side 20% flatter, right side unchanged.

Ellipse center (388.5, 235.5). Right radius rx_r = 142.6, left radius
rx_l = 142.6 * 0.8 = 114.1. ry = 181.1 unchanged. Built with a
super-ellipse-ish parametric curve: x = cx + rx(t)*cos(t) where
rx(t) = rx_l if cos(t)<0 else rx_r, with a smooth blend near the top/bottom
so the flat side tapers naturally into the vertical axis.
"""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
RAW_DIR = os.path.join(WS, "assets", "raw")
SRC = r"C:\Users\gru\Pictures\loj shavale"
FINAL = os.path.join(WS, "assets", "final")
SMALL = os.path.join(WS, "assets", "final_small")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

RAW_PATHS = sorted(
    os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR)
    if f.startswith("raw_f") and f.endswith(".png")
)[:53]
print(f"raw frames: {len(RAW_PATHS)}")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    tilt = math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))
    return (e1[0] + e2[0]) / 2, (e1[1] + e2[1]) / 2, tilt

body_full = Image.open(os.path.join(SRC, "300px-Donkey_Kong2.png")).convert("RGBA")
BW, BH = body_full.size
g_cx, g_cy = 388.5, 235.5
ry = 103.5 * 1.75          # 181.1 vertical
rx_r = 81.5 * 1.75         # 142.6 right (unchanged)
rx_l = rx_r * 0.80         # 114.1 left (20% flatter)
print(f"ellipse: ry={ry:.1f} rx_right={rx_r:.1f} rx_left={rx_l:.1f}")

def asymmetric_ellipse_mask(w, h, cx, cy, rx_l, rx_r, ry, blur=1.2):
    """Mask via parametric points: x(t)=cx+rx(t)cos t, y(t)=cy+ry sin t.
    rx(t) blends between rx_l (cos t<0) and rx_r (cos t>0) smoothly."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    pts = []
    N = 720
    for i in range(N):
        t = 2 * math.pi * i / N
        ct = math.cos(t)
        # smooth blend: weight = (ct+1)/2 -> 0 on left, 1 on right; sharpen a bit
        wgt = ((ct + 1) / 2) ** 3
        rx = rx_l * (1 - wgt) + rx_r * wgt
        pts.append((cx + rx * ct, cy + ry * math.sin(t)))
    d.polygon(pts, fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))

face_mask = asymmetric_ellipse_mask(BW, BH, g_cx, g_cy, rx_l, rx_r, ry, 1.2)

# Erase mask: same shape, slightly bigger on all sides
ERASE_MARGIN = 14 * 1.75
erase = asymmetric_ellipse_mask(
    BW, BH, g_cx, g_cy,
    rx_l + ERASE_MARGIN, rx_r + ERASE_MARGIN, ry + ERASE_MARGIN, 3.0)

def erase_head(body):
    a = body.getchannel("A")
    arr = np.array(a, dtype=np.float32)
    e = np.array(erase, dtype=np.float32) / 255.0
    arr = arr * (1.0 - e)
    body.putalpha(Image.fromarray(arr.astype(np.uint8), "L"))
    return body

BODY = erase_head(body_full.copy())
print("head erased")

def composite_gorilla(raw_path, out_path):
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size
    res = det.detect(mp.Image.create_from_file(raw_path))
    if not res.face_landmarks:
        return False
    lm = None
    for f in res.face_landmarks:
        if f[1].x * W >= W / 2:
            lm = f
            break
    if lm is None:
        return False
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)
    bl = BASE["right"]
    erx, ery = bl["rx"], bl["ry"]
    crop_w, crop_h = int(2 * erx), int(2 * ery)
    x0, y0 = int(emx - erx), int(emy - ery)
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(raw, (pxx, pyy))
        x0 += pxx; y0 += pyy
        raw = big
    crop = raw.crop((x0, y0, x0 + crop_w, y0 + crop_h))
    if abs(tilt) > 10:
        crop = crop.rotate(tilt, center=(crop_w / 2, crop_h / 2),
                           resample=Image.BICUBIC, expand=False)
    # Fill the asymmetric ellipse: scale to the right-side (bigger) extent,
    # then mask with the asymmetric shape.
    target_w, target_h = int(2 * rx_r), int(2 * ry)
    scale = max(target_w / crop_w, target_h / crop_h)
    crop = crop.resize((int(crop_w * scale), int(crop_h * scale)), Image.LANCZOS)
    cw, ch = crop.size
    # Center on the ellipse center
    px = int(g_cx - cw / 2)
    py = int(g_cy - ch / 2)
    mask_crop = face_mask.crop((px, py, px + cw, py + ch))
    face = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    face.paste(crop, (0, 0), crop)
    fa = np.array(face.getchannel("A"), dtype=np.float32)
    ma = np.array(mask_crop, dtype=np.float32)
    fa = np.minimum(fa, ma)
    face.putalpha(Image.fromarray(fa.astype(np.uint8), "L"))
    body = BODY.copy()
    body.alpha_composite(face, (px, py))
    body.save(out_path)
    return True

out_dir = os.path.join(FINAL, "gorilla")
os.makedirs(out_dir, exist_ok=True)
for f in os.listdir(out_dir):
    if f.endswith(".png"):
        os.remove(os.path.join(out_dir, f))
ok = 0
for i, rp in enumerate(RAW_PATHS):
    if composite_gorilla(rp, os.path.join(out_dir, f"f_{i+1:03d}.png")):
        ok += 1
print(f"gorilla: {ok}/{len(RAW_PATHS)} frames")

# Small: tight crop to opaque bbox, draw at 54x66 (same on-screen size as v31)
import os
dst_dir = os.path.join(SMALL, "gorilla")
os.makedirs(dst_dir, exist_ok=True)
for f in os.listdir(dst_dir):
    if f.endswith(".png"):
        os.remove(os.path.join(dst_dir, f))
TW, TH = 54, 66
for f in sorted(os.listdir(out_dir)):
    if not f.endswith(".png"):
        continue
    im = Image.open(os.path.join(out_dir, f)).convert("RGBA")
    a = np.array(im.getchannel("A"))
    ys, xs = np.where(a > 8)
    box = (max(0, xs.min()-2), max(0, ys.min()-2),
           min(im.size[0], xs.max()+3), min(im.size[1], ys.max()+3))
    im = im.crop(box).resize((TW, TH), Image.LANCZOS)
    im.save(os.path.join(dst_dir, f), optimize=True)
print(f"small gorilla: {TW}x{TH} (tight)")
print("done")
