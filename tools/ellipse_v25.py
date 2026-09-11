"""v25: crop the face region from the raw frame FIRST (using the contour
center), THEN apply the ellipse mask to the crop. This prevents the
dark video background from showing around the face."""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
RAW = os.path.join(WS, "assets", "raw", "raw_f001.png")
BODIES = os.path.join(WS, "assets", "bodies")
PREVIEW = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    tilt = math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))
    return (e1[0] + e2[0]) / 2, (e1[1] + e2[1]) / 2, tilt

def build(tag, side, body_path, body_head_xy, head_target_h):
    raw = Image.open(RAW).convert("RGBA")
    W, H = raw.size  # 800x800

    res = det.detect(mp.Image.create_from_file(RAW))
    if not res.face_landmarks:
        return None
    lm = None
    for f in res.face_landmarks:
        fx = f[1].x * W
        if (side == "left" and fx < W / 2) or (side == "right" and fx >= W / 2):
            lm = f; break
    if lm is None:
        return None
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)

    bl = BASE[side]
    erx, ery = bl["rx"], bl["ry"]
    if side == "left":
        off_x, off_y = 254 - emx, 411 - emy
    else:
        off_x, off_y = 691 - emx, 443 - emy
    cx = emx + off_x
    cy = emy + off_y

    # 1) CROP the face region from the raw frame FIRST
    margin = int(max(erx, ery) * 0.10)
    crop_w = int(2 * (erx + margin))
    crop_h = int(2 * (ery + margin))
    x0 = int(cx - crop_w / 2)
    y0 = int(cy - crop_h / 2)
    # pad if out of bounds
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(raw, (pxx, pyy))
        x0 += pxx; y0 += pyy
        raw = big
    face_crop = raw.crop((x0, y0, x0 + crop_w, y0 + crop_h))
    # face_crop is crop_w x crop_h, centered on the contour center

    # 2) Apply the ellipse mask to the crop (centered)
    erxi = int(erx); eryi = int(ery)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    # The ellipse is centered in the crop, but tilted by the face axis
    # First draw it axis-aligned, then rotate
    em = em.rotate(0)  # no-op
    edd.ellipse([crop_w // 2 - erxi, crop_h // 2 - eryi,
                 crop_w // 2 + erxi, crop_h // 2 + eryi], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    face_crop.putalpha(em)

    # 3) Upright only if tilt is large (rotate the crop)
    if abs(tilt) > 10:
        face_crop = face_crop.rotate(tilt, center=(crop_w / 2, crop_h / 2),
                                      resample=Image.BICUBIC, expand=False)

    # 4) Scale so 2*ery -> head_target_h
    scale = (head_target_h / 2.0) / eryi
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    face_crop = face_crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) Composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(face_crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v25_{tag}_f001.png")
    body.save(out)
    print(f"{tag}: tilt={tilt:+.1f} center=({cx:.0f},{cy:.0f}) new=({new_w},{new_h}) saved")
    return body

build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 140), 300)
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (121, 107), 215)
print("done")
