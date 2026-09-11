"""v29: respect body transparency, keep original proportions, scale uniformly.

- Roach: use cockroach_headless.png (RGBA, 358x734, transparent bg).
  Composite face onto it, keep 358x734 aspect. Scale uniformly 50% bigger
  than v27 (which drew at 24x49 on screen -> 36x74).
  Small frame: 72x147 (3x display of 24x49) — same as before.
  Wait: user said 50% bigger. v27 draw was 24x49. 50% bigger = 36x74.
  Small = 3x display = 108x222. But that changes the body aspect from
  358:734 to 108:222 = 0.486 vs 0.488 — close enough.
  Actually: 358/734 = 0.4878. 108/222 = 0.4865. Good.
  But the FACE was scaled to head_target_h=287 in v28 (50% of 230... wait
  230*1.5=345). The body stays the same size in the small frame; the face
  inside it is bigger relative to the body. That's the 50% bigger face.

- Gorilla: use gorilla_headless_new.jpg (980x980, black bg). The user
  says it's backgroundless. The black bg is part of the source. I'll
  keep it as-is (black on black game bg looks fine) but crop tighter
  to remove watermark margins. Keep the body's natural proportions.
  Small frame: 108x116 (from 820x880 crop).

Key: do NOT flatten transparent PNGs onto black. Save as PNG with alpha.
"""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
RAW_DIR = os.path.join(WS, "assets", "raw")
BODIES = os.path.join(WS, "assets", "bodies")
FINAL = os.path.join(WS, "assets", "final")
SMALL = os.path.join(WS, "assets", "final_small")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

RAW_PATHS = sorted(
    os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR)
    if f.startswith("raw_f") and f.endswith(".png")
)
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

def crop_face(raw, lm, W, H, side, bl_key):
    """Crop the face centered on eye_mid, sized to baseline ellipse."""
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)
    bl = BASE[bl_key]
    erx, ery = bl["rx"], bl["ry"]
    cx, cy = emx, emy
    crop_w = int(2 * erx)
    crop_h = int(2 * ery)
    x0 = int(cx - erx)
    y0 = int(cy - ery)
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(raw, (pxx, pyy))
        x0 += pxx; y0 += pyy
        raw = big
    crop = raw.crop((x0, y0, x0 + crop_w, y0 + crop_h))
    ccx, ccy = crop_w / 2, crop_h / 2
    if abs(tilt) > 10:
        crop = crop.rotate(tilt, center=(ccx, ccy), resample=Image.BICUBIC, expand=False)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([0, 0, crop_w - 1, crop_h - 1], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1.5))
    crop.putalpha(em)
    return crop, tilt

def find_face(res, W, side):
    for f in res.face_landmarks:
        fx = f[1].x * W
        if (side == "left" and fx < W / 2) or (side == "right" and fx >= W / 2):
            return f
    return None

# --- ROACH: transparent body, keep proportions, face 50% bigger ---
roach_body = Image.open(os.path.join(BODIES, "cockroach_headless.png")).convert("RGBA")
RBW, RBH = roach_body.size  # 358x734
print(f"roach body: {RBW}x{RBH} (RGBA, transparent)")
# Head anchor: the roach head is at the top. In v27 the anchor was (400,150)
# in the 800x800 raw frame space, but the body is 358x734. The head region
# is roughly centered horizontally, in the upper third.
roach_head_cx = RBW // 2  # 179
roach_head_cy = int(RBH * 0.19)  # ~140, upper portion

def composite_roach(raw_path, out_path):
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size
    res = det.detect(mp.Image.create_from_file(raw_path))
    if not res.face_landmarks:
        return False
    lm = find_face(res, W, "left")
    if lm is None:
        return False
    crop, _ = crop_face(raw, lm, W, H, "left", "left")
    # Scale face to 50% bigger than v27 (head_target_h was 230 -> 345)
    bl = BASE["left"]
    ery = bl["ery" if "ery" in bl else "ry"]
    head_target_h = 345
    scale = (head_target_h / 2.0) / ery
    new_w = int(crop.size[0] * scale)
    new_h = int(crop.size[1] * scale)
    crop = crop.resize((new_w, new_h), Image.LANCZOS)
    body = roach_body.copy()
    body.alpha_composite(crop, (roach_head_cx - new_w // 2, roach_head_cy - new_h // 2))
    # Save as PNG (preserve alpha)
    body.save(out_path)
    return True

# --- GORILLA: black-bg body, crop tight, keep proportions ---
gorilla_full = Image.open(os.path.join(BODIES, "gorilla_headless_new.jpg")).convert("RGBA")
# Crop to remove watermark margins
BODY_CROP = (80, 40, 900, 920)
gorilla_body = gorilla_full.crop(BODY_CROP)
GBW, GBH = gorilla_body.size  # 820x880
g_cx = 388.5 - BODY_CROP[0]  # 308.5
g_cy = 235.5 - BODY_CROP[1]  # 195.5
g_rx, g_ry = 81.5, 103.5
print(f"gorilla body: {GBW}x{GBH} (cropped)")

def composite_gorilla(raw_path, out_path):
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size
    res = det.detect(mp.Image.create_from_file(raw_path))
    if not res.face_landmarks:
        return False
    lm = find_face(res, W, "right")
    if lm is None:
        return False
    crop, _ = crop_face(raw, lm, W, H, "right", "right")
    target_w = int(2 * g_rx)
    target_h = int(2 * g_ry)
    scale = max(target_w / crop.size[0], target_h / crop.size[1])
    new_w = int(crop.size[0] * scale)
    new_h = int(crop.size[1] * scale)
    crop = crop.resize((new_w, new_h), Image.LANCZOS)
    body = gorilla_body.copy()
    body.alpha_composite(crop, (int(g_cx - new_w / 2), int(g_cy - new_h / 2)))
    # Gorilla body has black bg (JPEG source). Save as PNG.
    body.save(out_path)
    return True

for char, comp in [("roach", composite_roach), ("gorilla", composite_gorilla)]:
    out_dir = os.path.join(FINAL, char)
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(out_dir, f))
    ok = 0
    for i, rp in enumerate(RAW_PATHS[:53]):
        if comp(rp, os.path.join(out_dir, f"f_{i+1:03d}.png")):
            ok += 1
    print(f"{char}: {ok}/53 frames")

# --- final_small: keep original proportions, scale to display size ---
# Roach: body 358x734, display 36x74 (50% bigger than 24x49) -> 3x = 108x222
# Gorilla: body 820x880, display 40x43 -> 3x = 120x129
for char, dw, dh in [("roach", 108, 222), ("gorilla", 120, 129)]:
    src_dir = os.path.join(FINAL, char)
    dst_dir = os.path.join(SMALL, char)
    os.makedirs(dst_dir, exist_ok=True)
    for f in os.listdir(dst_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(dst_dir, f))
    for f in sorted(os.listdir(src_dir)):
        if not f.endswith(".png"):
            continue
        im = Image.open(os.path.join(src_dir, f)).convert("RGBA")
        im = im.resize((dw, dh), Image.LANCZOS)
        im.save(os.path.join(dst_dir, f), optimize=True)
    print(f"small {char}: {dw}x{dh}")

print("done")
