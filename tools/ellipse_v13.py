"""Per-frame rotated-ellipse face compositor v13.
Manually-tuned ellipse for frame 1, tracked by eye-line for subsequent frames.
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
    for idx, label in [(33,"eyeLout"),(133,"eyeLin"),(263,"eyeRout"),(362,"eyeRin")]:
        pts[label] = (lm[idx].x * W, lm[idx].y * H)
    return pts

def eye_line_angle(pts):
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    return math.degrees(math.atan2(eyeR[1]-eyeL[1], eyeR[0]-eyeL[0]))

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

def build_frame(face_name, body_path, body_head_xy, face_scale, frame, manual=None):
    """manual: (cx, cy, angle, rx, ry) in 400x400 space, or None to auto-detect."""
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    pts = get_landmarks(face_path)
    if pts is None:
        return None, None

    if manual:
        cx, cy, angle, rx, ry = manual
    else:
        # Auto: use eye line angle, center below eyes
        eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                         (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
        eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                         (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
        eye_mid = (eyeL + eyeR) / 2
        interocular = np.linalg.norm(eyeR - eyeL)
        e_angle = eye_line_angle(pts)
        # Perpendicular pointing down (toward mouth)
        px, py = math.sin(math.radians(e_angle)), -math.cos(math.radians(e_angle))
        if py < 0: px, py = -px, -py
        p_len = math.sqrt(px*px+py*py); px, py = px/p_len, py/p_len
        center_dist = interocular * 0.55
        cx = eye_mid[0] + px * center_dist
        cy = eye_mid[1] + py * center_dist
        angle = math.degrees(math.atan2(px, py))
        rx = interocular * 0.95
        ry = interocular * 1.35

    mask = draw_rotated_ellipse_mask(W, H, int(cx), int(cy), int(rx), int(ry), angle, feather=1)
    img.putalpha(mask)

    new_w = int(W * face_scale)
    new_h = int(H * face_scale)
    face_scaled = img.resize((new_w, new_h), Image.LANCZOS)
    fcx = int(cx * face_scale)
    fcy = int(cy * face_scale)

    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    pad = int(max(rx, ry) * face_scale * 1.3)
    zx0 = max(0, bx - pad); zy0 = max(0, by - pad)
    zx1 = min(a.shape[1], bx + pad); zy1 = min(a.shape[0], by + pad)
    zone[zy0:zy1, zx0:zx1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    body = Image.fromarray(a, "RGBA")
    body.alpha_composite(face_scaled, (bx - fcx, by - fcy))
    return body, (cx, cy, angle, rx, ry)

# Manual ellipse for frame 1 (tuned from visual inspection)
# Left face: center ~(200, 260), tilt -30 deg, rx=140, ry=170
# Right face: center ~(200, 240), tilt +10 deg, rx=130, ry=165
LEFT_MANUAL = (200, 260, -30, 140, 170)
RIGHT_MANUAL = (200, 240, 10, 130, 165)

ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
GOR_BODY = os.path.join(BODIES, "gorilla_full.png")

for name, body, head, scale, manual in [
    ("left", ROACH_BODY, (179, 168), 0.52, LEFT_MANUAL),
    ("right", GOR_BODY, (150, 60), 0.22, RIGHT_MANUAL),
]:
    body_img, params = build_frame(name, body, head, scale, 1, manual)
    if body_img is None:
        print(name, "NO FACE")
        continue
    tag = "roach" if name == "left" else "gorilla"
    bg = Image.new("RGBA", body_img.size, (90, 90, 100, 255))
    bg.alpha_composite(body_img)
    bg.convert("RGB").save(os.path.join(OUT, f"v13_{tag}_f001.jpg"), quality=90)
    cx, cy, angle, rx, ry = params
    print(f"{tag}: center=({cx:.0f},{cy:.0f}) angle={angle:.1f} r=({rx:.0f},{ry:.0f})")
print("done")
