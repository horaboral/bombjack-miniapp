"""v28b: gorilla composite — face centered, fills the white ellipse.

Fix: crop is centered on the ACTUAL face (eye_mid), not the old baseline
contour center. The baseline ellipse radii (erx, ery) define the crop size.
After cropping, the face is at the center of the crop. We then scale the
crop to fit the body's white ellipse and paste at the ellipse center.
"""
import os, math, json
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

gorilla_body = Image.open(os.path.join(BODIES, "gorilla_headless_new.jpg")).convert("RGBA")
GBW, GBH = gorilla_body.size
g_cx, g_cy = 388.5, 235.5
g_rx, g_ry = 81.5, 103.5

# Crop the body to remove watermark text and empty black margins.
# Content: head top ~y=60, feet ~y=880, left arm ~x=100, right arm ~x=850
BODY_CROP = (80, 40, 900, 920)  # (left, top, right, bottom)
body_crop = gorilla_body.crop(BODY_CROP)
BCW, BCH = body_crop.size  # 820x880
# Adjust ellipse center to crop coords
g_cx -= BODY_CROP[0]
g_cy -= BODY_CROP[1]
print(f"body crop: {BCW}x{BCH}, ellipse center=({g_cx:.1f},{g_cy:.1f})")

def composite_gorilla_frame(raw_path, out_path):
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size

    res = det.detect(mp.Image.create_from_file(raw_path))
    if not res.face_landmarks:
        return False
    lm = None
    for f in res.face_landmarks:
        fx = f[1].x * W
        if fx >= W / 2:
            lm = f; break
    if lm is None:
        return False
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)

    # Crop centered on the ACTUAL face (eye_mid), sized to the baseline ellipse
    bl = BASE["right"]
    erx, ery = bl["rx"], bl["ry"]
    cx, cy = emx, emy  # face center, not baseline center
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

    # Ellipse mask: full-crop ellipse so the face edge follows the shape
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([0, 0, crop_w - 1, crop_h - 1], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1.5))
    crop.putalpha(em)

    # Scale to fit the body's white ellipse
    target_w = int(2 * g_rx)
    target_h = int(2 * g_ry)
    scale = max(target_w / crop_w, target_h / crop_h)
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    crop = crop.resize((new_w, new_h), Image.LANCZOS)

    body = body_crop.copy()
    px = int(g_cx - new_w / 2)
    py = int(g_cy - new_h / 2)
    body.alpha_composite(crop, (px, py))
    body.convert("RGB").save(out_path, quality=92)
    return True

out_dir = os.path.join(FINAL, "gorilla")
os.makedirs(out_dir, exist_ok=True)
ok = 0
for i, rp in enumerate(RAW_PATHS):
    out = os.path.join(out_dir, f"f_{i+1:03d}.png")
    if composite_gorilla_frame(rp, out):
        ok += 1
print(f"gorilla: {ok}/{len(RAW_PATHS)} frames")

# Compress to final_small
src_dir = os.path.join(FINAL, "gorilla")
dst_dir = os.path.join(SMALL, "gorilla")
os.makedirs(dst_dir, exist_ok=True)
# Remove old frames
for f in os.listdir(dst_dir):
    if f.endswith(".png"):
        os.remove(os.path.join(dst_dir, f))
for f in sorted(os.listdir(src_dir)):
    if not f.endswith(".png"):
        continue
    im = Image.open(os.path.join(src_dir, f))
    # Body crop is 820x880; keep aspect in small frames
    im = im.resize((108, 116), Image.LANCZOS)
    im.save(os.path.join(dst_dir, f), optimize=True)
print("small gorilla: 108x116")
print("done")
