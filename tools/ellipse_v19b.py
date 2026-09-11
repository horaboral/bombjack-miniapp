"""v19b: user contour shape (baseline_ellipses.json rx/ry) centered on the
per-frame MediaPipe head center, rotated by eye-line tilt, uprighted, then
composited onto the user headless bodies. Frame-1 validation."""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
BODIES = os.path.join(WS, "assets", "bodies")
PREVIEW = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]

def eye_tilt_of(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    return math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))

def build(tag, side, body_path, body_head_xy, head_target_h):
    face_path = os.path.join(FACES, side, "f_001.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size

    res = det.detect(mp.Image.create_from_file(face_path))
    if not res.face_landmarks:
        return None
    lm = res.face_landmarks[0]
    tilt = eye_tilt_of(lm, W, H)
    # Center = eye-line midpoint (robust; the raw-head contour centroid is
    # unreliable when detection is partial)
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    cx = (e1[0] + e2[0]) / 2
    cy = (e1[1] + e2[1]) / 2
    # The eye-line midpoint sits above the head center; shift the ellipse
    # center down by ~22% of the tall radius so it covers forehead + chin.
    bl_ = BASE[side]
    cy += bl_["ry"] * (W / 800.0) * 0.22

    # User baseline shape: rx (wide) / ry (tall) in 800x800 raw coords.
    # Crop is 400x400 from the 800x800 raw => scale 0.5.
    bl = BASE[side]
    s = W / 800.0
    erx = bl["rx"] * s          # wide radius in crop coords
    ery = bl["ry"] * s          # tall radius in crop coords

    # 1) source-space mask, centered on the head center, aligned with the
    #    face's own axis (rotated CW by tilt for a CW-tilted face)
    pad = int(max(erx, ery) * 1.6)
    cw, ch = W + 2 * pad, H + 2 * pad
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    px, py = pad + cx, pad + cy
    dd.ellipse([px - erx, py - ery, px + erx, py + ery], fill=255)
    m = m.rotate(-tilt, center=(px, py), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad + W, pad + H))
    m.save(os.path.join(PREVIEW, f"v19_debug_mask_{side}.png"))
    img.putalpha(m)

    # 2) upright: only the left face needs rotation (tilt +25 deg).
    #    The right face is already nearly vertical (tilt -3 deg) — skip.
    if abs(tilt) > 10:
        img = img.rotate(tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)
        tilt_applied = tilt
    else:
        tilt_applied = 0

    # head center after rotation about canvas center
    rad = math.radians(tilt_applied)  # rotation actually applied (PIL)
    dx = cx - W / 2
    dy = cy - H / 2
    new_cx = dx * math.cos(rad) - dy * math.sin(rad) + W / 2
    new_cy = dx * math.sin(rad) + dy * math.cos(rad) + H / 2

    margin = int(max(erx, ery) * 0.12)
    crop_w = int(2 * (erx + margin))
    crop_h = int(2 * (ery + margin))
    x0 = int(new_cx - crop_w / 2)
    y0 = int(new_cy - crop_h / 2)
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(img, (pxx, pyy))
        x0 += pxx; y0 += pyy
        img = big
    head_crop = img.crop((x0, y0, x0 + crop_w, y0 + crop_h))

    # 3) vertical tight ellipse (user shape)
    erxi = int(erx); eryi = int(ery)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erxi, crop_h // 2 - eryi,
                 crop_w // 2 + erxi, crop_h // 2 + eryi], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    # 4) scale so 2*ery -> head_target_h
    scale = (head_target_h / 2.0) / eryi
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) composite onto user headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v19_{tag}_f001.png")
    body.save(out)
    print(f"{tag}: tilt={tilt:+.1f} center=({cx:.0f},{cy:.0f}) er=({erx:.0f},{ery:.0f}) saved")
    return body

build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 210), 300)
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (150, 62), 105)
print("done")
