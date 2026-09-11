"""Per-frame rotated-ellipse face compositor v10.
- Detects face landmarks per frame in the 400x400 crop
- Computes a rotated-ellipse transform (face frame -> body frame)
- Applies the transform to the 400x400 face crop, producing a body-sized face
  with a sharp rotated-ellipse alpha, then composites onto the body.
- CORRECTED mapping: left face (laughing) -> cockroach, right face (talking) -> gorilla
"""
import os, math
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter, ImageTransform

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
    """Return (cx, cy, angle, rx, ry) in the 400x400 face space.
    - center: nose-to-chin midpoint shifted 20% toward chin (includes mouth+neck)
    - angle: face tilt (0 = upright, + = clockwise)
    - rx: half-width (a bit more than interocular/2)
    - ry: half-height (eyeMid-to-chin * 0.8)
    """
    eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2,
                     (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
    eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2,
                     (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
    eyeMid = (eyeL + eyeR) / 2
    noseTip = np.array(pts["noseTip"])
    chin = np.array(pts["chin"])
    v = chin - eyeMid
    angle = math.degrees(math.atan2(v[0], -v[1]))
    center = (noseTip + chin) / 2 + (chin - noseTip) * 0.20
    interocular = np.linalg.norm(eyeR - eyeL)
    ry = np.linalg.norm(chin - eyeMid) * 0.80
    rx = interocular * 0.92
    return (center[0], center[1], angle, rx, ry)

def build_frame(face_name, body_path, body_head_xy, target_ry, frame):
    """target_ry: desired half-height of the face ellipse in BODY pixels.
    The 400x400 face is transformed so that its detected ellipse maps to
    an ellipse centered at body_head_xy with half-height target_ry, same
    aspect and same rotation."""
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    pts = get_landmarks(face_path)
    if pts is None:
        return None, None

    fcx, fcy, angle, frx, fry = face_params(pts)
    scale = target_ry / fry
    target_rx = frx * scale
    bfx, bfy = body_head_xy

    # Transform: face(x,y) -> body.
    # body = R(angle) * S(scale) * (face - fc) + bf
    # => face = S^-1 * R(-angle) * (body - bf) + fc
    # PIL affine: out[x,y] = in[a*x+b*y+c, d*x+e*y+f]
    ca, sa = math.cos(math.radians(-angle)), math.sin(math.radians(-angle))
    a = ca / scale; b = sa / scale
    d = -sa / scale; e = ca / scale
    c = fcx - a*bfx - b*bfy
    f = fcy - d*bfx - e*bfy

    # Output canvas: body-sized region around the head
    cw = int(2 * (target_rx + 20))
    ch = int(2 * (target_ry + 20))
    # local coords: (0,0) = top-left of canvas; body_head at (cw/2, ch/2)
    a2 = a; b2 = b
    d2 = d; e2 = e
    c2 = c - a*(cw//2) - b*(ch//2)
    f2 = f - d*(cw//2) - e*(ch//2)
    face_canvas = img.transform((cw, ch), Image.AFFINE,
                                 (a2, b2, c2, d2, e2, f2), resample=Image.BILINEAR)

    # Rotated-ellipse alpha in canvas space (center = canvas center)
    erx, ery = int(target_rx), int(target_ry)
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    dd.ellipse([cw//2 - erx, ch//2 - ery, cw//2 + erx, ch//2 + ery], fill=255)
    m = m.rotate(angle, center=(cw//2, ch//2), resample=Image.BICUBIC)
    m = m.filter(ImageFilter.GaussianBlur(1))
    face_canvas.putalpha(m)

    # Body: clear head zone, composite
    body = Image.open(body_path).convert("RGBA")
    a = np.array(body)
    zone = np.zeros(a.shape[:2], np.uint8)
    zx0 = max(0, bfx - cw//2 - 6); zy0 = max(0, bfy - ch//2 - 6)
    zx1 = min(a.shape[1], bfx + cw//2 + 6); zy1 = min(a.shape[0], bfy + ch//2 + 6)
    zone[zy0:zy1, zx0:zx1] = 255
    zm = np.array(Image.fromarray(zone).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a[..., 3] = (a[..., 3] * (1 - zm)).astype(np.uint8)
    body = Image.fromarray(a, "RGBA")
    body.alpha_composite(face_canvas, (bfx - cw//2, bfy - ch//2))
    return body, (fcx, fcy, angle, frx, fry, scale)

# target_ry in body pixels:
# Cockroach 358x734: face ~ 110px half-height (220px tall) - fits head zone
# Gorilla 300x232: face ~ 42px half-height (84px tall)
ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
GOR_BODY = os.path.join(BODIES, "gorilla_full.png")

for name, body, head, try_ in [
    ("left", ROACH_BODY, (179, 168), 105),
    ("right", GOR_BODY, (150, 60), 40),
]:
    body_img, params = build_frame(name, body, head, try_, 1)
    if body_img is None:
        print(name, "NO FACE")
        continue
    tag = "roach" if name == "left" else "gorilla"
    bg = Image.new("RGBA", body_img.size, (90, 90, 100, 255))
    bg.alpha_composite(body_img)
    bg.convert("RGB").save(os.path.join(OUT, f"v10_{tag}_f001.jpg"), quality=90)
    fcx, fcy, angle, frx, fry, sc = params
    print(f"{tag}: face=({fcx:.0f},{fcy:.0f}) angle={angle:.1f} r=({frx:.0f},{fry:.0f}) scale={sc:.3f}")
print("done")
