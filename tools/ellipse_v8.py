"""Per-frame rotated-ellipse face compositor v8.
- Detects face landmarks per frame
- Crops a tight square around the face (clamped to 400x400 bounds)
- Applies a rotated ellipse mask aligned to the face tilt
- Scales onto the body's head zone
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

def face_params(pts, W, H):
    """Return (cx, cy, angle, rx, ry) in the FULL 400x400 face space.
    The ellipse is centered on the face (nose-to-chin region), rotated to
    match the face tilt, sized to include mouth + a bit of neck."""
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    eyeMid = (eyeL + eyeR) / 2
    noseTip = np.array(pts["noseTip"])
    chin = np.array(pts["chin"])

    v = chin - eyeMid
    angle = math.degrees(math.atan2(v[0], -v[1]))

    # Center: between noseTip and chin, shifted 20% toward chin (include mouth+neck)
    center = (noseTip + chin) / 2 + (chin - noseTip) * 0.2

    interocular = np.linalg.norm(eyeR - eyeL)
    ry = np.linalg.norm(chin - eyeMid) * 0.80  # half-height: covers eye-to-chin + neck
    rx = interocular * 0.92                    # half-width: a bit more than eye span

    return (int(center[0]), int(center[1]), angle, int(rx), int(ry))

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

    cx, cy, angle, rx, ry = face_params(pts, W, H)

    # Apply rotated ellipse mask to the full 400x400 face
    face = img.convert("RGBA")
    mask = draw_rotated_ellipse_mask(W, H, cx, cy, rx, ry, angle, feather=1)
    face.putalpha(mask)

    # Scale the 400x400 face to target width
    scale = face_target_w / W
    new_w = face_target_w
    new_h = int(H * scale)
    face_scaled = face.resize((new_w, new_h), Image.LANCZOS)

    # Clear body head zone
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zx0 = max(0, bx - new_w//2 - 8); zy0 = max(0, by - new_h//2 - 8)
    zx1 = min(a.shape[1], bx + new_w//2 + 8); zy1 = min(a.shape[0], by + new_h//2 + 8)
    zone[zy0:zy1, zx0:zx1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    body = Image.fromarray(a, "RGBA")

    # Paste centered on body head
    body.alpha_composite(face_scaled, (bx - new_w//2, by - new_h//2))
    return body, (cx, cy, angle, rx, ry)

# Parameters
ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
ROACH_HEAD = (179, 175)
ROACH_W = 210

GOR_BODY = os.path.join(BODIES, "gorilla_full.png")
GOR_HEAD = (150, 62)
GOR_W = 88

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
    bg.convert("RGB").save(os.path.join(OUT, f"v8_{tag}_f001.jpg"), quality=90)
    cx, cy, angle, rx, ry = params
    print(f"{tag}: ellipse=({cx},{cy}) angle={angle:.1f} r=({rx},{ry})")
print("done")
