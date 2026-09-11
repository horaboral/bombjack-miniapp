"""Per-frame rotated-ellipse face compositor v12.
Uses EYE LINE (not chin) for orientation, since chin landmarks may fall
outside the 400x400 crop. The ellipse center is placed a fixed distance
below the eye midpoint, perpendicular to the eye line (toward the mouth).
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
    for idx, label in [(1,"noseTip"),(33,"eyeLout"),(133,"eyeLin"),(263,"eyeRout"),(362,"eyeRin")]:
        pts[label] = (lm[idx].x * W, lm[idx].y * H)
    return pts

def face_params_eye(pts):
    """Return (cx, cy, angle, rx, ry) using ONLY eye landmarks.
    - eye_mid: midpoint between the two eye centers
    - eye_angle: angle of the eye line from horizontal
    - ellipse center: eye_mid shifted DOWN (perpendicular to eye line, toward mouth)
    - angle: face tilt (ellipse major axis aligned with face vertical)
    """
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    eye_mid = (eyeL + eyeR) / 2
    interocular = np.linalg.norm(eyeR - eyeL)

    # Eye line angle from horizontal (image coords: y down)
    dx = eyeR[0] - eyeL[0]
    dy = eyeR[1] - eyeL[1]
    eye_angle = math.degrees(math.atan2(dy, dx))

    # Face vertical: perpendicular to eye line, pointing "down" (toward mouth)
    # In image coords, "down" is +y. The perpendicular to (dx,dy) pointing down
    # is (dy, -dx) normalized, if that points down; else (-dy, dx).
    px, py = dy, -dx
    # Check if this points "down" (positive y component in image space)
    # We want the direction from eyes toward mouth (downward)
    # The mouth is below the eyes in face space, which in image space depends on tilt
    # For a roughly upright face, mouth is at larger y, so we want +y component
    if py < 0:
        px, py = -px, -py
    p_len = math.sqrt(px*px + py*py)
    px, py = px/p_len, py/p_len

    # Ellipse center: eye_mid + distance * (px, py)
    # Distance from eyes to center of face (nose/mouth area): ~0.55 * interocular
    center_dist = interocular * 0.55
    cx = eye_mid[0] + px * center_dist
    cy = eye_mid[1] + py * center_dist

    # Ellipse rotation: face vertical angle from image vertical
    # Face vertical direction: (px, py). Image vertical: (0, 1).
    # Angle between them: atan2(px, py) ... no.
    # The ellipse major axis should align with the face vertical (px, py).
    # PIL rotate() rotates counterclockwise. The angle of (px,py) from the
    # positive y-axis (down) is: atan2(px, py) in standard math, but in image
    # coords with y-down, it's: atan2(px, py) gives angle from +y toward +x.
    # For PIL: rotate(angle) rotates the image CCW. We want the ellipse's
    # major axis (originally vertical) to point along (px, py).
    # The angle to rotate = angle of (px,py) measured from (0,1) [straight down]
    # toward (1,0) [right]. That's atan2(px, py).
    angle = math.degrees(math.atan2(px, py))

    # Ellipse radii
    rx = interocular * 0.95   # half-width
    ry = interocular * 1.35   # half-height (covers eyes through mouth + neck)

    return (cx, cy, angle, rx, ry)

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

def build_frame(face_name, body_path, body_head_xy, face_scale, frame):
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    pts = get_landmarks(face_path)
    if pts is None:
        return None, None

    cx, cy, angle, rx, ry = face_params_eye(pts)

    # Apply rotated ellipse mask to the 400x400 face
    mask = draw_rotated_ellipse_mask(W, H, int(cx), int(cy), int(rx), int(ry), angle, feather=1)
    img.putalpha(mask)

    # Scale
    new_w = int(W * face_scale)
    new_h = int(H * face_scale)
    face_scaled = img.resize((new_w, new_h), Image.LANCZOS)

    # Face center in scaled space
    fcx = int(cx * face_scale)
    fcy = int(cy * face_scale)

    # Clear body head zone
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

    # Paste so face center lands on body head
    body.alpha_composite(face_scaled, (bx - fcx, by - fcy))
    return body, (cx, cy, angle, rx, ry)

# Parameters
ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
ROACH_HEAD = (179, 168)
ROACH_SCALE = 0.52

GOR_BODY = os.path.join(BODIES, "gorilla_full.png")
GOR_HEAD = (150, 60)
GOR_SCALE = 0.22

for name, body, head, scale in [
    ("left", ROACH_BODY, ROACH_HEAD, ROACH_SCALE),
    ("right", GOR_BODY, GOR_HEAD, GOR_SCALE),
]:
    body_img, params = build_frame(name, body, head, scale, 1)
    if body_img is None:
        print(name, "NO FACE")
        continue
    tag = "roach" if name == "left" else "gorilla"
    bg = Image.new("RGBA", body_img.size, (90, 90, 100, 255))
    bg.alpha_composite(body_img)
    bg.convert("RGB").save(os.path.join(OUT, f"v12_{tag}_f001.jpg"), quality=90)
    cx, cy, angle, rx, ry = params
    print(f"{tag}: center=({cx:.0f},{cy:.0f}) angle={angle:.1f} r=({rx:.0f},{ry:.0f})")
print("done")
