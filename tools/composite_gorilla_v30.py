"""v30: gorilla from the ORIGINAL transparent PNG body.

- Body: 300px-Donkey_Kong2.png (RGBA, 980x980, transparent bg).
- Erase the head region using the user's white ellipse (from the headless
  jpg) as a guide: make everything inside the ellipse (plus a small margin
  ring) fully transparent, so no old head pixels remain.
- Composite the face (right video face) onto the ellipse: same ellipse
  region, so the face fills exactly where the user marked.
- Face must be BIGGER than before: it fills the full ellipse (rx=81.5,
  ry=103.5 -> 163x207), which is much larger relative to the body than
  the previous composites (the old face was a tiny crop inside that).
- Save as transparent PNG, no black anywhere.
"""
import os, math, json
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

# --- body from the transparent PNG ---
body_full = Image.open(os.path.join(SRC, "300px-Donkey_Kong2.png")).convert("RGBA")
print(f"body: {body_full.size} mode={body_full.mode}")
BW, BH = body_full.size  # 980x980

# Ellipse from the user's drawing (measured on the headless jpg, same 980x980 space)
g_cx, g_cy = 388.5, 235.5
g_rx, g_ry = 81.5, 103.5

# Erase the head: clear a slightly larger ellipse around the drawn one
# (so the old head hair/edges don't peek out around the new face).
ERASE_MARGIN = 14  # px beyond the drawn ellipse
erase = Image.new("L", (BW, BH), 0)
ed = ImageDraw.Draw(erase)
ed.ellipse([g_cx - g_rx - ERASE_MARGIN, g_cy - g_ry - ERASE_MARGIN,
            g_cx + g_rx + ERASE_MARGIN, g_cy + g_ry + ERASE_MARGIN], fill=255)
erase = erase.filter(ImageFilter.GaussianBlur(3.0))

# Face mask: exactly the drawn ellipse
face_mask = Image.new("L", (BW, BH), 0)
fd = ImageDraw.Draw(face_mask)
fd.ellipse([g_cx - g_rx, g_cy - g_ry, g_cx + g_rx, g_cy + g_ry], fill=255)
face_mask = face_mask.filter(ImageFilter.GaussianBlur(1.2))

def erase_head(body):
    """Set alpha to 0 inside the erase ellipse (smooth edge)."""
    a = body.getchannel("A")
    import numpy as np
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

    # Scale the crop to FILL the drawn ellipse (163x207) — much bigger face.
    target_w, target_h = int(2 * g_rx), int(2 * g_ry)
    scale = max(target_w / crop_w, target_h / crop_h)
    crop = crop.resize((int(crop_w * scale), int(crop_h * scale)), Image.LANCZOS)
    cw, ch = crop.size

    # Apply the drawn-ellipse mask (cropped to the paste region)
    px = int(g_cx - cw / 2)
    py = int(g_cy - ch / 2)
    mask_crop = face_mask.crop((px, py, px + cw, py + ch))

    # Build the face layer: crop with the ellipse mask as alpha
    face = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    face.paste(crop, (0, 0), crop)  # use crop's own alpha (ellipse from crop)
    # Combine: face alpha = min(crop alpha, drawn-ellipse mask)
    import numpy as np
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

# Small: keep body aspect 980x980 -> 120x120 (bigger than the 40x43 before)
dst_dir = os.path.join(SMALL, "gorilla")
os.makedirs(dst_dir, exist_ok=True)
for f in os.listdir(dst_dir):
    if f.endswith(".png"):
        os.remove(os.path.join(dst_dir, f))
for f in sorted(os.listdir(out_dir)):
    if not f.endswith(".png"):
        continue
    im = Image.open(os.path.join(out_dir, f)).convert("RGBA")
    im = im.resize((120, 120), Image.LANCZOS)
    im.save(os.path.join(dst_dir, f), optimize=True)
print("small gorilla: 120x120")
print("done")
