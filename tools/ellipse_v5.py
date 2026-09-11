"""Per-frame rotated-ellipse face compositor v5.
- Detects face landmarks per frame via MediaPipe FaceLandmarker
- Fits a rotated ellipse aligned to the face's vertical axis (nose-derived)
- Ellipse includes mouth + a bit of neck, sharp edges (1px feather)
- CORRECTED mapping: left face (laughing) -> cockroach, right face (talking) -> gorilla
"""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
BODIES = os.path.join(WS, "assets", "bodies")
OUT = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
os.makedirs(OUT, exist_ok=True)

# MediaPipe FaceLandmarker
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
                        (61,"mouthL"),(291,"mouthR"),(105,"mouthCtr"),
                        (6,"glabella"),(178,"lowerLip")]:
        pts[label] = (lm[idx].x * W, lm[idx].y * H)
    return pts

def face_frame(pts):
    """Return (center_x, center_y, angle_deg, face_height, face_width) from landmarks.
    face_height = distance from top-of-head (estimated above eyes) to below chin (neck).
    face_width  = inter-ocular distance scaled.
    angle = tilt of the face's vertical axis (0 = upright, positive = clockwise).
    """
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    eyeMid = (eyeL + eyeR) / 2
    noseTip = np.array(pts["noseTip"])
    chin = np.array(pts["chin"])

    # face vertical axis: from eyeMid to chin (this is the "up" direction of the face)
    v = chin - eyeMid
    # angle of this vector from vertical (0, -1)
    # in image coords, up is -y. angle = atan2(vx, -vy)
    angle = math.degrees(math.atan2(v[0], -v[1]))

    # face center: weighted toward the mouth area (to include mouth + neck)
    # center is between noseTip and chin, shifted slightly toward chin
    center = (noseTip + chin) / 2
    # shift center down (toward chin/neck) by 15% of noseTip-chin distance
    d = chin - noseTip
    center = center + d * 0.15

    # face dimensions
    interocular = np.linalg.norm(eyeR - eyeL)
    face_height = np.linalg.norm(chin - eyeMid) * 1.55  # extend below chin for neck
    face_width = interocular * 1.7

    return (center[0], center[1], angle, face_height, face_width)

def draw_rotated_ellipse(size, cx, cy, rx, ry, angle_deg, feather=1):
    """Draw a rotated ellipse on a mask of given size."""
    W, H = size
    # Create a larger canvas to avoid clipping the rotated ellipse
    pad = int(max(rx, ry) * 0.6)
    cw, ch = W + 2*pad, H + 2*pad
    m = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(m)
    # Draw the ellipse on the padded canvas, centered at (pad+W//2, pad+H//2)
    ecx, ecy = pad + W//2, pad + H//2
    d.ellipse([ecx-rx, ecy-ry, ecx+rx, ecy+ry], fill=255)
    # Rotate around the ellipse center
    m = m.rotate(angle_deg, center=(ecx, ecy), resample=Image.BICUBIC, expand=False)
    # Crop back to the original size
    m = m.crop((pad, pad, pad+W, pad+H))
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m

def clear_zone(body, box, blur=8):
    x0, y0, x1, y1 = box
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zone[y0:y1, x0:x1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")

def build_frame(face_name, body_path, body_head_center, body_scale, frame):
    """Build one frame: detect face, fit ellipse, composite onto body.
    body_head_center: (x,y) where the face ellipse center goes on the body.
    body_scale: scale factor from 400x400 face coords to body coords.
    """
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    pts = get_landmarks(face_path)
    if pts is None:
        print(f"  {face_name} f{frame:03d}: NO FACE DETECTED")
        return None, None

    cx, cy, angle, fh, fw = face_frame(pts)
    # Map face coords to body coords
    bcx = int(body_head_center[0] + (cx - 200) * body_scale)
    bcy = int(body_head_center[1] + (cy - 200) * body_scale)
    brx = int(fw * 0.5 * body_scale)
    bry = int(fh * 0.5 * body_scale)

    body = Image.open(body_path).convert("RGBA")
    # Clear the head zone (a bit larger than the ellipse)
    pad = int(max(brx, bry) * 0.3)
    body = clear_zone(body, (bcx-brx-pad, bcy-bry-pad, bcx+brx+pad, bcy+bry+pad))

    # Create face canvas at 400x400 (face crop size)
    face = Image.open(face_path).convert("RGB").convert("RGBA")
    # Draw rotated ellipse mask at face resolution
    f_rx = int(fw * 0.5)
    f_ry = int(fh * 0.5)
    mask = draw_rotated_ellipse((400, 400), int(cx), int(cy), f_rx, f_ry, angle, feather=1)
    face.putalpha(mask)

    # Scale face to body size and paste
    scale = body_scale
    new_w = int(400 * scale)
    new_h = int(400 * scale)
    face = face.resize((new_w, new_h), Image.LANCZOS)
    px = bcx - new_w // 2
    py = bcy - new_h // 2
    body.alpha_composite(face, (px, py))

    return body, (cx, cy, angle, fh, fw)

# --- Parameters per character ---
# Cockroach: 358x734. Head center ~ (179, 170). Scale: face ellipse should be ~190px wide on body.
# Face ellipse width in 400x400 coords ~ 190px, so scale = 190/190 = 1.0? No.
# The body is 358 wide, face should be ~55% of body width = ~197px.
# In face coords, face_width ~ interocular * 1.7. For left face, interocular ~ 200px,
# so face_width ~ 340px in 400x400. Scale = 197/340 = 0.58.
ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
ROACH_CENTER = (179, 175)
ROACH_SCALE = 0.55

# Gorilla: 300x232. Head center ~ (150, 62). Face should be ~25% of body width = ~75px.
# In face coords, face_width ~ 300px. Scale = 75/300 = 0.25.
GOR_BODY = os.path.join(BODIES, "gorilla_full.png")
GOR_CENTER = (150, 62)
GOR_SCALE = 0.24

# Process frame 1 for each
for name, body, center, scale in [
    ("left", ROACH_BODY, ROACH_CENTER, ROACH_SCALE),
    ("right", GOR_BODY, GOR_CENTER, GOR_SCALE),
]:
    body_img, params = build_frame(name, body, center, scale, 1)
    if body_img is None:
        continue
    tag = "roach" if name == "left" else "gorilla"
    bg = Image.new("RGBA", body_img.size, (90, 90, 100, 255))
    bg.alpha_composite(body_img)
    bg.convert("RGB").save(os.path.join(OUT, f"v5_{tag}_f001.jpg"), quality=90)
    cx, cy, angle, fh, fw = params
    print(f"{tag}: center=({cx:.0f},{cy:.0f}) angle={angle:.1f}deg fh={fh:.0f} fw={fw:.0f}")
print("done")
