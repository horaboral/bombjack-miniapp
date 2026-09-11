"""v23: work on the raw 800x800 frame. Mask = contour ellipse AND the
video's circular photo frame (exclude the black video background).
Upright the left face, scale to head target, composite onto headless bodies.
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

def video_circle_mask(W, H):
    """Detect the video's circular photo frame: the largest region of
    non-dark pixels. Returns a mask (255 = inside photo)."""
    arr = np.array(Image.open(RAW).convert("RGB"), dtype=np.int16)
    lum = arr.mean(axis=2)
    # Photo pixels: brightness > 40 (the video background is near-black)
    photo = lum > 40
    # Find the bounding circle: use the centroid and max radius of photo pixels
    ys, xs = np.nonzero(photo)
    cx = float(xs.mean()); cy = float(ys.mean())
    r = float(np.sqrt(((xs - cx) ** 2 + (ys - cy) ** 2)).max())
    # Build a circular mask
    yy, xx = np.mgrid[0:H, 0:W]
    circ = ((xx - cx) ** 2 + (yy - cy) ** 2) <= (r * 0.98) ** 2
    m = Image.fromarray((circ * 255).astype(np.uint8), "L")
    print(f"  video circle: center=({cx:.0f},{cy:.0f}) r={r:.0f}")
    return m

def build(tag, side, body_path, body_head_xy, head_target_h):
    img = Image.open(RAW).convert("RGBA")
    W, H = img.size  # 800x800

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

    # 1) contour ellipse mask
    m_ell = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(m_ell)
    dd.ellipse([cx - erx, cy - ery, cx + erx, cy + ery], fill=255)
    m_ell = m_ell.rotate(-tilt, center=(cx, cy), resample=Image.BICUBIC)

    # 2) video circle mask (exclude black background)
    m_circ = video_circle_mask(W, H)

    # Combine: intersection
    m = Image.new("L", (W, H), 0)
    import numpy as _np
    arr_m = _np.minimum(_np.array(m_ell), _np.array(m_circ))
    m = Image.fromarray(arr_m, "L")
    img.putalpha(m)

    # 3) upright only if tilt is large
    if abs(tilt) > 10:
        img = img.rotate(tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)
        tilt_applied = tilt
    else:
        tilt_applied = 0

    rad = math.radians(tilt_applied)
    dx = cx - W / 2; dy = cy - H / 2
    new_cx = dx * math.cos(rad) - dy * math.sin(rad) + W / 2
    new_cy = dx * math.sin(rad) + dy * math.cos(rad) + H / 2

    margin = int(max(erx, ery) * 0.10)
    crop_w = int(2 * (erx + margin)); crop_h = int(2 * (ery + margin))
    x0 = int(new_cx - crop_w / 2); y0 = int(new_cy - crop_h / 2)
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(img, (pxx, pyy))
        x0 += pxx; y0 += pyy
        img = big
    head_crop = img.crop((x0, y0, x0 + crop_w, y0 + crop_h))

    # 4) vertical tight ellipse
    erxi = int(erx); eryi = int(ery)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erxi, crop_h // 2 - eryi,
                 crop_w // 2 + erxi, crop_h // 2 + eryi], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    # 5) scale
    scale = (head_target_h / 2.0) / eryi
    new_w = int(crop_w * scale); new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # 6) composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v23_{tag}_f001.png")
    body.save(out)
    print(f"{tag}: tilt={tilt:+.1f} center=({cx:.0f},{cy:.0f}) new=({new_w},{new_h}) saved")
    return body

build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 140), 380)
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (121, 107), 215)
print("done")
