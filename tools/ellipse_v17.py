"""Per-frame full-head upright compositor v17.
- Fits the ellipse to the EXTENDED head contour per frame
- Uprights the face by rotating the source by the EYE-LINE tilt angle
  (reliable, inside the crop)
- Masks to the ellipse in SOURCE space BEFORE rotating, so no background
  square shows through
- Uses pre-processed headless bodies (no runtime clear zone)
- Tight full-head ellipse, sharp 1px feather
- CORRECTED mapping: left face (laughing) -> cockroach, right face (talking) -> gorilla
"""
import os, math
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
BODIES = os.path.join(WS, "assets", "bodies")
OUT = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
os.makedirs(OUT, exist_ok=True)

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]
EYE_L_OUT, EYE_L_IN = 33, 133
EYE_R_IN, EYE_R_OUT = 362, 263

def detect(path):
    res = det.detect(mp.Image.create_from_file(path))
    if not res.face_landmarks:
        return None
    W, H = Image.open(path).size
    lm = res.face_landmarks[0]
    head = np.array([(lm[i].x * W, lm[i].y * H) for i in HEAD_BASE], dtype=np.float64)
    eye_l = ((lm[EYE_L_OUT].x * W + lm[EYE_L_IN].x * W) / 2,
             (lm[EYE_L_OUT].y * H + lm[EYE_L_IN].y * H) / 2)
    eye_r = ((lm[EYE_R_IN].x * W + lm[EYE_R_OUT].x * W) / 2,
             (lm[EYE_R_IN].y * H + lm[EYE_R_OUT].y * H) / 2)
    return head, eye_l, eye_r, W, H

def extend_head(pts, W, H):
    out = pts.copy()
    # Push top up more (forehead/hair) - 18% of image height
    for i in range(9):
        out[i, 1] = max(0, out[i, 1] - 0.18 * H)
    # Push bottom down (neck) - 8%
    for i in range(20, len(out)):
        out[i, 1] = min(H, out[i, 1] + 0.08 * H)
    # Widen sides 6%
    cx = out[:, 0].mean()
    for i in range(9, 20):
        out[i, 0] = cx + (out[i, 0] - cx) * 1.06
    return out

def fit_ellipse(pts):
    center = pts.mean(axis=0)
    c = pts - center
    cov = np.cov(c.T)
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, np.argmax(evals)]
    minor = evecs[:, np.argmin(evals)]
    if major[1] < 0:
        major = -major
    minor = minor - (minor @ major) * major
    minor /= np.linalg.norm(minor)
    ry = float(np.percentile(np.abs(c @ major), 92) * 0.98)
    rx = float(np.percentile(np.abs(c @ minor), 92) * 0.98)
    return center, major, minor, rx, ry

def eye_tilt(eye_l, eye_r):
    """Return the tilt angle in degrees. 0 = upright.
    Positive = right side lower (face tilted CW)."""
    dx = eye_r[0] - eye_l[0]
    dy = eye_r[1] - eye_l[1]
    return math.degrees(math.atan2(dy, dx))

def build_frame(face_name, body_path, body_head_xy, head_target_h, frame):
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    det_result = detect(face_path)
    if det_result is None:
        return None, None
    head, eye_l, eye_r, W, H = det_result

    extended = extend_head(head, W, H)
    center, major, minor, rx, ry = fit_ellipse(extended)
    tilt = eye_tilt(eye_l, eye_r)

    # Step 1: Create ellipse mask in SOURCE space (rotated ellipse)
    angle = math.degrees(math.atan2(major[0], major[1]))
    # Make the ellipse big enough to cover the canvas
    pad = int(max(rx, ry) * 1.5)
    cw, ch = W + 2 * pad, H + 2 * pad
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    cx, cy = pad + center[0], pad + center[1]
    dd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    m = m.rotate(angle, center=(cx, cy), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad + W, pad + H))
    # Apply mask to source image
    img.putalpha(m)

    # Step 2: Rotate the masked image by -tilt to upright the face
    # PIL rotate(angle) rotates CCW. If tilt is +25 (right side lower),
    # we need to rotate CCW by 25 to bring the right side up.
    img = img.rotate(-tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)

    # Step 3: After rotation, the ellipse center moves.
    # The original center was at (center[0], center[1]) in the 400x400 image.
    # After rotation around (W/2, H/2) by -tilt degrees:
    # new_center = rotate(center - W/2, -tilt) + W/2
    rad = math.radians(-tilt)
    dx = center[0] - W / 2
    dy = center[1] - H / 2
    new_cx = dx * math.cos(rad) - dy * math.sin(rad) + W / 2
    new_cy = dx * math.sin(rad) + dy * math.cos(rad) + W / 2

    # Step 4: Crop around the new center with the ellipse radii + margin
    # After rotation, the ellipse is approximately axis-aligned (upright)
    # Use the original radii (rx, ry) since rotation preserves size
    margin = int(max(rx, ry) * 0.15)
    crop_w = int(2 * (rx + margin))
    crop_h = int(2 * (ry + margin))
    x0 = int(new_cx - crop_w / 2)
    y0 = int(new_cy - crop_h / 2)
    # Pad if out of bounds
    px = max(0, -x0); py = max(0, -y0)
    nx = max(0, x0 + crop_w - W); ny = max(0, y0 + crop_h - H)
    if px or py or nx or ny:
        big = Image.new("RGBA", (W + px + nx, H + py + ny), (0, 0, 0, 0))
        big.paste(img, (px, py))
        x0 += px; y0 += py
        img = big
    head_crop = img.crop((x0, y0, x0 + crop_w, y0 + crop_h))

    # Step 5: Create a vertical (upright) ellipse mask for the crop
    # The ellipse center in the crop is at (crop_w/2, crop_h/2)
    erx = int(rx); ery = int(ry)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erx, crop_h // 2 - ery,
                 crop_w // 2 + erx, crop_h // 2 + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    # Step 6: Scale to target size
    scale = (head_target_h / 2.0) / ry
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # Step 7: Composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    return body, (center, rx, ry, tilt)

ROACH_BODY = os.path.join(BODIES, "cockroach_headless.png")
GOR_BODY = os.path.join(BODIES, "gorilla_headless.png")

for name, body, head_xy, th in [
    ("left", ROACH_BODY, (179, 175), 230),
    ("right", GOR_BODY, (150, 75), 110),
]:
    body_img, params = build_frame(name, body, head_xy, th, 1)
    if body_img is None:
        print(name, "NO FACE")
        continue
    tag = "roach" if name == "left" else "gorilla"
    bg = Image.new("RGBA", body_img.size, (90, 90, 100, 255))
    bg.alpha_composite(body_img)
    bg.convert("RGB").save(os.path.join(OUT, f"v17_{tag}_f001.jpg"), quality=90)
    center, rx, ry, tilt = params
    print(f"{tag}: center=({center[0]:.0f},{center[1]:.0f}) r=({rx:.0f},{ry:.0f}) tilt={tilt:+.1f}")
print("done")
