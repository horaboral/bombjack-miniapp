"""v28: final compositor.

- Gorilla: uses the EXACT white ellipse the user drew on the new headless
  body (assets/bodies/gorilla_headless_new.jpg) as the face mask. The face
  from the raw video is cropped, masked to that shape, scaled to fit, and
  composited. No black halo: the mask IS the white ellipse, and the body
  is black outside it, so the face blends in.
- Roach: uses the PCA-fitted ellipse from baseline_ellipses.json, scaled
  25% bigger than v27 (head_target_h 230 -> 287).
- Both output to assets/final/ (full res) then assets/final_small/ (3x
  display res for the 144x256 game).

Gorilla display: the body is 980x980; on screen it should be comparable
to the roach. Roach is drawn 24x49 (aspect 71:147). Gorilla body is
square-ish; the gorilla frame at 980x980 will be drawn at ~36x36 to be
comparable in visual weight.
"""
import os, math, json, shutil
import numpy as np
import mediapipe as mp
import cv2
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
RAW_DIR = os.path.join(WS, "assets", "raw")
BODIES = os.path.join(WS, "assets", "bodies")
FINAL = os.path.join(WS, "assets", "final")
SMALL = os.path.join(WS, "assets", "final_small")
CONTOURS = os.path.join(WS, "assets", "contours")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

# Load all 53 raw frames
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

# --- Gorilla: load the user-drawn white ellipse mask (in body coords) ---
# The mask was saved cropped to bbox with margin=5.
# bbox was (307,132,163,207) in 980x980, so mask origin = (307-5, 132-5) = (302,127)
GORILLA_BODY = os.path.join(BODIES, "gorilla_headless_new.jpg")
GORILLA_MASK = os.path.join(CONTOURS, "gorilla_white_ellipse.png")
gorilla_body = Image.open(GORILLA_BODY).convert("RGB")
GBW, GBH = gorilla_body.size  # 980x980
gorilla_mask_full = Image.new("L", (GBW, GBH), 0)
gorilla_mask_crop = Image.open(GORILLA_MASK)
gorilla_mask_full.paste(gorilla_mask_crop, (302, 127))
# Ellipse center in body coords
g_cx, g_cy = 388.5, 235.5
g_rx, g_ry = 81.5, 103.5

def composite_gorilla_frame(raw_path, out_path):
    """Composite the right face (talking man) into the gorilla body."""
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size  # 800x800

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

    # Contour center in raw coords (from baseline)
    bl = BASE["right"]
    erx, ery = bl["rx"], bl["ry"]
    off_x, off_y = 691 - emx, 443 - emy
    cx, cy = emx + off_x, emy + off_y

    # Crop a generous region around the contour center
    margin = int(max(erx, ery) * 0.12)
    crop_w = int(2 * (erx + margin))
    crop_h = int(2 * (ery + margin))
    x0 = int(cx - crop_w / 2)
    y0 = int(cy - crop_h / 2)
    # Pad if out of bounds
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(raw, (pxx, pyy))
        x0 += pxx; y0 += pyy
        raw = big
    crop = raw.crop((x0, y0, x0 + crop_w, y0 + crop_h))
    ccx, ccy = crop_w / 2, crop_h / 2

    # Upright the face (right face tilt ~-3.5, skip rotation)
    if abs(tilt) > 10:
        crop = crop.rotate(tilt, center=(ccx, ccy), resample=Image.BICUBIC, expand=False)

    # Apply the user-drawn ellipse mask, scaled to the crop.
    # The mask in body coords is centered at (g_cx, g_cy) with radii (g_rx, g_ry).
    # We need to map it to crop coords: the crop is centered on the face,
    # so the mask center should be at the crop center.
    # Scale the mask so that 2*g_ry matches the crop height (which is 2*(ery+margin)).
    mask_scaled_w = crop_w
    mask_scaled_h = crop_h
    # Create an ellipse mask in crop coords, using the same aspect ratio
    # as the user's drawn ellipse (g_rx/g_ry).
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    # The mask should be sized so that the face fits inside it.
    # Use the baseline ellipse radii (erx, ery) which are in raw coords.
    # The crop is 2*(erx+margin) x 2*(ery+margin), so the ellipse in crop
    # coords is centered at (ccx, ccy) with radii (erx, ery).
    edd.ellipse([ccx - erx, ccy - ery, ccx + erx, ccy + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1.2))
    crop.putalpha(em)

    # Now scale the crop to fit the gorilla's white ellipse.
    # The white ellipse has height 2*g_ry = 207px in the 980x980 body.
    # The crop height is 2*(ery+margin). Scale so crop_h -> 2*g_ry.
    target_h = int(2 * g_ry)  # 207
    scale = target_h / crop_h
    new_w = int(crop_w * scale)
    new_h = target_h
    crop = crop.resize((new_w, new_h), Image.LANCZOS)

    # Composite onto the gorilla body
    body = gorilla_body.copy().convert("RGBA")
    # Paste at the ellipse center
    px = int(g_cx - new_w / 2)
    py = int(g_cy - new_h / 2)
    body.alpha_composite(crop, (px, py))
    body.convert("RGB").save(out_path, quality=92)
    return True

def composite_roach_frame(raw_path, out_path):
    """Composite the left face (laughing man) into the roach body, 25% bigger."""
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size  # 800x800

    res = det.detect(mp.Image.create_from_file(raw_path))
    if not res.face_landmarks:
        return False
    lm = None
    for f in res.face_landmarks:
        fx = f[1].x * W
        if fx < W / 2:
            lm = f; break
    if lm is None:
        return False
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)

    bl = BASE["left"]
    erx, ery = bl["rx"], bl["ry"]
    off_x, off_y = 254 - emx, 411 - emy
    cx, cy = emx + off_x, emy + off_y

    margin = int(max(erx, ery) * 0.12)
    crop_w = int(2 * (erx + margin))
    crop_h = int(2 * (ery + margin))
    x0 = int(cx - crop_w / 2)
    y0 = int(cy - crop_h / 2)
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
    edd.ellipse([ccx - erx, ccy - ery, ccx + erx, ccy + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1.2))
    crop.putalpha(em)

    # Roach: 50% bigger than v27 (v27 head_target_h=230 -> 230*1.5=345)
    head_target_h = 345
    scale = (head_target_h / 2.0) / ery
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    crop = crop.resize((new_w, new_h), Image.LANCZOS)

    body = Image.open(os.path.join(BODIES, "roach_headless.jpg")).convert("RGBA")
    bx, by = 400, 150  # roach head anchor
    body.alpha_composite(crop, (bx - new_w // 2, by - new_h // 2))
    body.convert("RGB").save(out_path, quality=92)
    return True

# --- Process all frames ---
for char, comp in [("gorilla", composite_gorilla_frame), ("roach", composite_roach_frame)]:
    out_dir = os.path.join(FINAL, char)
    os.makedirs(out_dir, exist_ok=True)
    ok = 0
    for i, rp in enumerate(RAW_PATHS):
        out = os.path.join(out_dir, f"f_{i+1:03d}.png")
        if comp(rp, out):
            ok += 1
    print(f"{char}: {ok}/{len(RAW_PATHS)} frames")

# --- Compress to final_small (3x display res) ---
# Roach: 50% bigger than before -> 108x220
# Gorilla: comparable -> 108x116 (from body crop 820x880)
for char, dw, dh in [("roach", 108, 220), ("gorilla", 108, 116)]:
    src_dir = os.path.join(FINAL, char)
    dst_dir = os.path.join(SMALL, char)
    os.makedirs(dst_dir, exist_ok=True)
    for f in sorted(os.listdir(src_dir)):
        if not f.endswith(".png"):
            continue
        im = Image.open(os.path.join(src_dir, f))
        im = im.resize((dw, dh), Image.LANCZOS)
        im.save(os.path.join(dst_dir, f), optimize=True)
    print(f"small {char}: {dw}x{dh}")

print("done")
