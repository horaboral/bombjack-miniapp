"""v20: use the user contour's ACTUAL center and size (baseline_ellipses.json)
as the mask. Map the 800x800 contour center into the 400x400 face crop,
align the mask with the face axis, upright the left face, then composite
onto the user headless bodies. Frame-1 validation."""
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

def eye_tilt_of(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    return math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0])), e1, e2

def build(tag, side, body_path, body_head_xy, head_target_h):
    face_path = os.path.join(FACES, side, "f_001.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size  # 400x400 crop from 800x800 raw

    res = det.detect(mp.Image.create_from_file(face_path))
    if not res.face_landmarks:
        return None
    lm = res.face_landmarks[0]
    tilt, e1, e2 = eye_tilt_of(lm, W, H)

    # User contour in 800x800 raw coords -> crop coords (scale 0.5)
    bl = BASE[side]
    s = W / 800.0
    # Contour center in raw coords; the crop is the left (or right) 400x400
    # quadrant of the 800x800 raw. Left face crop = raw[0:400, 0:400].
    # So raw (x, y) -> crop (x - 0, y - 0) for left; (x - 400, y - 0) for right.
    ox = 0 if side == "left" else 400
    cx = (bl["center"][0] - ox) * s
    cy = bl["center"][1] * s
    erx = bl["rx"] * s   # wide radius in crop coords
    ery = bl["ry"] * s   # tall radius in crop coords

    # 1) source-space mask at the contour's own center/size, aligned to face axis
    pad = int(max(erx, ery) * 1.3)
    cw, ch = W + 2 * pad, H + 2 * pad
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    px, py = pad + cx, pad + cy
    dd.ellipse([px - erx, py - ery, px + erx, py + ery], fill=255)
    # align mask with the face's tilted axis
    m = m.rotate(-tilt, center=(px, py), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad + W, pad + H))
    m.save(os.path.join(PREVIEW, f"v20_debug_mask_{side}.png"))
    img.putalpha(m)

    # 2) upright only the left face (large tilt); right face skip
    if abs(tilt) > 10:
        img = img.rotate(tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)
        tilt_applied = tilt
    else:
        tilt_applied = 0

    # contour center after rotation about canvas center
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

    # 4) scale so 2*ery -> head_target_h
    scale = (head_target_h / 2.0) / eryi
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) composite onto user headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v20_{tag}_f001.png")
    body.save(out)
    print(f"{tag}: tilt={tilt:+.1f} center=({cx:.0f},{cy:.0f}) er=({erx:.0f},{ery:.0f}) "
          f"new=({new_w},{new_h}) saved")
    return body

build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 210), 300)
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (150, 62), 105)
print("done")
