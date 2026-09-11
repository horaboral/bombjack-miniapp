"""v22: work directly on the raw 800x800 frame (no 400x400 crop).
User contour center/size from baseline_ellipses.json, per-frame eye-line
tilt from MediaPipe on the raw frame. Upright the left face, mask with the
contour ellipse, scale to head target, composite onto headless bodies.
Frame-1 validation."""
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
    img = Image.open(RAW).convert("RGBA")
    W, H = img.size  # 800x800

    res = det.detect(mp.Image.create_from_file(RAW))
    if not res.face_landmarks:
        return None
    # pick the face on the correct side
    lm = None
    for f in res.face_landmarks:
        fx = f[1].x * W
        if (side == "left" and fx < W / 2) or (side == "right" and fx >= W / 2):
            lm = f
            break
    if lm is None:
        return None
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)

    # User contour in raw coords (1:1, no scaling needed)
    bl = BASE[side]
    erx = bl["rx"]
    ery = bl["ry"]
    # Offset from eye midpoint to contour center (measured from frame 1)
    # left:  contour center (254,411), eye mid raw = emx, emy (computed)
    # right: contour center (691,443)
    if side == "left":
        off_x = 254 - emx
        off_y = 411 - emy
    else:
        off_x = 691 - emx
        off_y = 443 - emy
    cx = emx + off_x
    cy = emy + off_y

    print(f"{tag}: eye_mid=({emx:.0f},{emy:.0f}) tilt={tilt:+.1f} "
          f"contour_center=({cx:.0f},{cy:.0f}) er=({erx:.0f},{ery:.0f})")

    # 1) mask the raw frame with the contour ellipse (aligned to face axis)
    pad = 0
    m = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(m)
    dd.ellipse([cx - erx, cy - ery, cx + erx, cy + ery], fill=255)
    m = m.rotate(-tilt, center=(cx, cy), resample=Image.BICUBIC)
    img.putalpha(m)

    # 2) upright only if tilt is large (left face)
    if abs(tilt) > 10:
        img = img.rotate(tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)
        tilt_applied = tilt
    else:
        tilt_applied = 0

    # center after rotation about canvas center
    rad = math.radians(tilt_applied)
    dx = cx - W / 2
    dy = cy - H / 2
    new_cx = dx * math.cos(rad) - dy * math.sin(rad) + W / 2
    new_cy = dx * math.sin(rad) + dy * math.cos(rad) + H / 2

    margin = int(max(erx, ery) * 0.10)
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

    # 3) vertical tight ellipse at contour size
    erxi = int(erx); eryi = int(ery)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erxi, crop_h // 2 - eryi,
                 crop_w // 2 + erxi, crop_h // 2 + eryi], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    # 4) scale: content must fit INSIDE the ellipse (zoomed out).
    # The contour ellipse already spans the full head; scale the whole
    # crop so 2*ery maps to head_target_h.
    scale = (head_target_h / 2.0) / eryi
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v22_{tag}_f001.png")
    body.save(out)
    print(f"  new=({new_w},{new_h}) saved {out}")
    return body

build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 140), 260)
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (121, 107), 95)
print("done")
