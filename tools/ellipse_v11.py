"""Per-frame rotated-ellipse face compositor v11.
- Detects face landmarks per frame
- Crops a tight region around the face (forehead to below-chin/neck)
- Applies a rotated ellipse mask aligned to the face tilt
- Scales the crop onto the body's head zone
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

def get_landmarks(path):
    res = det.detect(mp.Image.create_from_file(path))
    if not res.face_landmarks:
        return None
    W, H = Image.open(path).size
    lm = res.face_landmarks[0]
    pts = {}
    for idx, label in [(1,"noseTip"),(4,"noseBase"),(152,"chin"),
                        (33,"eyeLout"),(133,"eyeLin"),(263,"eyeRout"),(362,"eyeRin"),
                        (61,"mouthL"),(291,"mouthR"),(6,"glabella"),(178,"lowerLip")]:
        pts[label] = (lm[idx].x * W, lm[idx].y * H)
    return pts

def face_crop_and_ellipse(pts, W, H):
    """Return (crop_x, crop_y, crop_w, crop_h, ellipse_cx, ellipse_cy, angle, rx, ry)
    all in the CROPPED face space.
    """
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    eyeMid = (eyeL + eyeR) / 2
    noseTip = np.array(pts["noseTip"])
    chin = np.array(pts["chin"])
    glabella = np.array(pts["glabella"])

    # Face vertical axis
    v = chin - eyeMid
    angle = math.degrees(math.atan2(v[0], -v[1]))

    # Ellipse center in full-crop space: between glabella and chin, shifted toward chin
    center_full = (glabella + chin) / 2 + (chin - glabella) * 0.15

    # Ellipse radii
    interocular = np.linalg.norm(eyeR - eyeL)
    ry_full = np.linalg.norm(chin - eyeMid) * 0.70  # half-height
    rx_full = interocular * 0.85                    # half-width

    # Crop region: from above glabella to below chin (include neck)
    # Top: glabella.y - 0.5 * (glabella.y - eyeMid.y)  (a bit above the brow)
    top = glabella[1] - 0.4 * (glabella[1] - eyeMid[1])
    # Bottom: chin.y + 0.5 * (chin.y - noseTip[1])  (below chin, into neck)
    bottom = chin[1] + 0.4 * (chin[1] - noseTip[1])
    # Left/right: interocular extent
    left = eyeMid[0] - interocular * 0.75
    right = eyeMid[0] + interocular * 0.75

    # Make it square (use the larger dimension)
    w = right - left
    h = bottom - top
    size = max(w, h) * 1.1  # 10% margin
    cx_full = (left + right) / 2
    cy_full = (top + bottom) / 2

    crop_x = int(cx_full - size / 2)
    crop_y = int(cy_full - size / 2)
    crop_w = int(size)
    crop_h = int(size)

    # Clamp to image bounds
    crop_x = max(0, min(crop_x, W - crop_w))
    crop_y = max(0, min(crop_y, H - crop_h))

    # Ellipse center in cropped space
    ex = int(center_full[0] - crop_x)
    ey = int(center_full[1] - crop_y)
    rx = int(rx_full)
    ry = int(ry_full)

    return (crop_x, crop_y, crop_w, crop_h, ex, ey, angle, rx, ry)

def draw_rotated_ellipse_mask(W, H, cx, cy, rx, ry, angle_deg, feather=1):
    pad = int(max(rx, ry) * 0.7)
    cw, ch = W + 2*pad, H + 2*pad
    m = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([pad+cx-rx, pad+cy-ry, pad+cx+rx, pad+cy+ry], fill=255)
    m = m.rotate(angle_deg, center=(pad+cx, pad+cy), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad+W, pad+H))
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m

def build_frame(face_name, body_path, body_head_xy, face_target_w, frame):
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path)
    W, H = img.size
    pts = get_landmarks(face_path)
    if pts is None:
        return None, None

    crop_x, crop_y, crop_w, crop_h, ex, ey, angle, rx, ry = face_crop_and_ellipse(pts, W, H)

    # Crop the face region
    face_crop = img.crop((crop_x, crop_y, crop_x+crop_w, crop_y+crop_h)).convert("RGBA")

    # Apply rotated ellipse mask
    mask = draw_rotated_ellipse_mask(crop_w, crop_h, ex, ey, rx, ry, angle, feather=1)
    face_crop.putalpha(mask)

    # Scale to target width
    scale = face_target_w / crop_w
    new_w = face_target_w
    new_h = int(crop_h * scale)
    face_scaled = face_crop.resize((new_w, new_h), Image.LANCZOS)

    # Clear body head zone
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    pad = 10
    zx0 = max(0, bx - new_w//2 - pad); zy0 = max(0, by - new_h//2 - pad)
    zx1 = min(a.shape[1], bx + new_w//2 + pad); zy1 = min(a.shape[0], by + new_h//2 + pad)
    zone[zy0:zy1, zx0:zx1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    body = Image.fromarray(a, "RGBA")

    # Paste centered on body head
    body.alpha_composite(face_scaled, (bx - new_w//2, by - new_h//2))
    return body, (ex, ey, angle, rx, ry, crop_w, crop_h)

# Parameters
ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
ROACH_HEAD = (179, 165)
ROACH_W = 195

GOR_BODY = os.path.join(BODIES, "gorilla_full.png")
GOR_HEAD = (150, 58)
GOR_W = 82

for name, body, head, fw in [
    ("left", ROACH_BODY, ROACH_HEAD, ROACH_W),
    ("right", GOR_BODY, GOR_HEAD, GOR_W),
]:
    body_img, params = build_frame(name, body, head, fw, 1)
    if body_img is None:
        print(name, "NO FACE")
        continue
    tag = "roach" if name == "left" else "gorilla"
    bg = Image.new("RGBA", body_img.size, (90, 90, 100, 255))
    bg.alpha_composite(body_img)
    bg.convert("RGB").save(os.path.join(OUT, f"v11_{tag}_f001.jpg"), quality=90)
    ex, ey, angle, rx, ry, cw, ch = params
    print(f"{tag}: ellipse=({ex},{ey}) angle={angle:.1f} r=({rx},{ry}) crop={cw}x{ch}")
print("done")
