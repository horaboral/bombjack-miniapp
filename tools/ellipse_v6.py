"""Per-frame rotated-ellipse face compositor v6.
- Detects face landmarks per frame
- Creates a 400x400 face canvas with a rotated ellipse aligned to the face
- Scales and positions the canvas on the body's head zone
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
                        (61,"mouthL"),(291,"mouthR"),(178,"lowerLip")]:
        pts[label] = (lm[idx].x * W, lm[idx].y * H)
    return pts

def face_params(pts):
    """Return (cx, cy, angle_deg, rx, ry) for the ellipse in 400x400 face space.
    The ellipse is centered on the face, rotated to match the face tilt,
    sized to include mouth + a bit of neck.
    """
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    eyeMid = (eyeL + eyeR) / 2
    noseTip = np.array(pts["noseTip"])
    chin = np.array(pts["chin"])

    # Face vertical axis: eyeMid -> chin
    v = chin - eyeMid
    angle = math.degrees(math.atan2(v[0], -v[1]))

    # Center: between noseTip and chin, shifted toward chin (to include mouth+neck)
    center = (noseTip + chin) / 2 + (chin - noseTip) * 0.2

    # Ellipse radii in face space
    interocular = np.linalg.norm(eyeR - eyeL)
    ry = np.linalg.norm(chin - eyeMid) * 0.85  # half-height: eye to chin + a bit
    rx = interocular * 0.95                    # half-width: a bit more than eye span

    return (center[0], center[1], angle, rx, ry)

def draw_rotated_ellipse_mask(W, H, cx, cy, rx, ry, angle_deg, feather=1):
    """Draw a rotated ellipse mask of size (W,H) with center (cx,cy),
    radii (rx,ry), rotated angle_deg. Returns a PIL L image."""
    pad = int(max(rx, ry) * 0.7)
    cw, ch = W + 2*pad, H + 2*pad
    m = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(m)
    ecx, ecy = pad + cx, pad + cy
    d.ellipse([ecx-rx, ecy-ry, ecx+rx, ecy+ry], fill=255)
    m = m.rotate(angle_deg, center=(ecx, ecy), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad+W, pad+H))
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m

def build_frame(face_name, body_path, body_head_xy, face_scale, frame):
    """body_head_xy: where the face center should land on the body.
    face_scale: how much to scale the 400x400 face canvas to fit the body.
    """
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    pts = get_landmarks(face_path)
    if pts is None:
        return None, None

    cx, cy, angle, rx, ry = face_params(pts)

    # 1. Build 400x400 face canvas with rotated ellipse
    face = Image.open(face_path).convert("RGB").convert("RGBA")
    mask = draw_rotated_ellipse_mask(400, 400, int(cx), int(cy), int(rx), int(ry), angle, feather=1)
    face.putalpha(mask)

    # 2. Scale the 400x400 canvas to body size
    new_size = int(400 * face_scale)
    face_scaled = face.resize((new_size, new_size), Image.LANCZOS)

    # 3. Clear the body head zone (a bit larger than the face canvas)
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    pad = int(new_size * 0.15)
    # Clear zone
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zx0 = max(0, bx - new_size//2 - pad); zy0 = max(0, by - new_size//2 - pad)
    zx1 = min(a.shape[1], bx + new_size//2 + pad); zy1 = min(a.shape[0], by + new_size//2 + pad)
    zone[zy0:zy1, zx0:zx1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    body = Image.fromarray(a, "RGBA")

    # 4. Paste the scaled face canvas onto the body, centered at body_head_xy
    px = bx - new_size // 2
    py = by - new_size // 2
    body.alpha_composite(face_scaled, (px, py))

    return body, (cx, cy, angle, rx, ry)

# Parameters
ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
ROACH_HEAD = (179, 170)  # where the face center lands on the cockroach
ROACH_SCALE = 0.52       # 400*0.52 = 208px face canvas on a 358px body

GOR_BODY = os.path.join(BODIES, "gorilla_full.png")
GOR_HEAD = (150, 62)
GOR_SCALE = 0.22         # 400*0.22 = 88px face canvas on a 300px body

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
    bg.convert("RGB").save(os.path.join(OUT, f"v6_{tag}_f001.jpg"), quality=90)
    cx, cy, angle, rx, ry = params
    print(f"{tag}: cx={cx:.0f} cy={cy:.0f} angle={angle:.1f} rx={rx:.0f} ry={ry:.0f}")
print("done")
