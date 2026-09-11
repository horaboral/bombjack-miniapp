"""Per-frame full-head upright compositor v16.
- Fits the ellipse to the EXTENDED head contour (forehead/hair + face + neck)
- Uses a rotation matrix (not PIL transform) to map the tilted head to
  upright output space - avoids PIL affine quirks
- Uses pre-processed headless bodies (no runtime clear zone, no blur halo)
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

# Extended head contour: forehead/hair on top, face oval, jaw, plus neck extension
HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]

def detect(path):
    res = det.detect(mp.Image.create_from_file(path))
    if not res.face_landmarks:
        return None
    W, H = Image.open(path).size
    lm = res.face_landmarks[0]
    pts = np.array([(lm[i].x * W, lm[i].y * H) for i in HEAD_BASE], dtype=np.float64)
    return pts, W, H

def extend_head(pts, W, H):
    """Extend the contour: push top up (forehead/hair), bottom down (neck),
    widen sides slightly."""
    out = pts.copy()
    for i in range(9):
        out[i, 1] = max(0, out[i, 1] - 0.10 * H)
    for i in range(20, len(out)):
        out[i, 1] = min(H, out[i, 1] + 0.06 * H)
    cx = out[:, 0].mean()
    for i in range(9, 20):
        out[i, 0] = cx + (out[i, 0] - cx) * 1.04
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
    ry = float(np.percentile(np.abs(c @ major), 92) * 0.97)
    rx = float(np.percentile(np.abs(c @ minor), 92) * 0.97)
    return center, major, minor, rx, ry

def build_frame(face_name, body_path, body_head_xy, head_target_h, frame):
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    pts, W, H = detect(face_path)
    if pts is None:
        return None, None

    extended = extend_head(pts, W, H)
    center, major, minor, rx, ry = fit_ellipse(extended)

    # Output: vertical ellipse, height = head_target_h
    out_ry = head_target_h / 2.0
    out_rx = out_ry * (rx / ry)
    scale = out_ry / ry

    # Rotation: we want to map the face's major axis to vertical (0,1) in output.
    # major = (mx, my) in image space (y down). We want R * major = (0, 1).
    # R = [[cos, -sin], [sin, cos]]  (standard rotation)
    # R * [mx; my] = [0; 1]
    # cos*mx - sin*my = 0  =>  tan = mx/my  =>  angle = atan2(mx, my)
    # sin*mx + cos*my = 1  (scales the length, but we handle scale separately)
    # Actually: R * major / |major| = (0,1) means R rotates major to (0,1).
    # The angle to rotate major by is: angle = atan2(mx, my) - pi/2 ... let me think.
    # If major = (0, 1) (already pointing down), we want no rotation: angle=0.
    # atan2(0, 1) = 0. Good.
    # If major = (1, 0) (pointing right), we want to rotate it to (0,1): 90 deg CW.
    # atan2(1, 0) = pi/2 = 90 deg. In image coords (y down), CW rotation by 90
    # takes (1,0) to (0,1). So angle = atan2(mx, my) gives the CW rotation angle.
    # PIL rotate(angle) rotates COUNTERclockwise. So we need rotate(-angle) in PIL.
    # But we're not using PIL rotate - we're using a rotation matrix.
    # R_cw(theta) = [[cos, sin], [-sin, cos]]  (CW rotation in image coords, y down)
    # Check: R_cw(90) * (1,0) = (cos90, -sin90) = (0, -1). That's UP, not down.
    # Hmm. Let me use: R(theta) = [[cos, -sin], [sin, cos]] (CCW in standard math).
    # In image coords (y down), this is actually CW visually.
    # R(90) * (1,0) = (0, 1). Yes! That's what we want.
    # So: theta = atan2(mx, my) and R = [[cos, -sin], [sin, cos]]
    theta = math.atan2(major[0], major[1])
    ct, st = math.cos(theta), math.sin(theta)

    # Output canvas
    pad = int(out_ry * 0.15)
    cw = int(2 * (out_rx + pad))
    ch = int(2 * (out_ry + pad))
    ccx, ccy = cw // 2, ch // 2

    # For each output pixel (ox, oy) relative to canvas center:
    #   out_vec = (ox, oy)
    #   in_vec = R^T * (1/scale) * out_vec + center
    #   R^T = [[cos, sin], [-sin, cos]]
    #   in_x = (cos*ox + sin*oy) / scale + center_x
    #   in_y = (-sin*ox + cos*oy) / scale + center_y
    # PIL affine: out[x,y] = in[a*x + b*y + c, d*x + e*y + f]
    # where x,y are output pixel coords (not relative to center)
    a = ct / scale
    b = st / scale
    d = -st / scale
    e = ct / scale
    c = center[0] - a * ccx - b * ccy
    f = center[1] - d * ccx - e * ccy

    head = img.transform((cw, ch), Image.AFFINE,
                          (a, b, c, d, e, f), resample=Image.BILINEAR)

    # Vertical ellipse mask (sharp, 1px feather)
    erx = int(out_rx); ery = int(out_ry)
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    dd.ellipse([ccx - erx, ccy - ery, ccx + erx, ccy + ery], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1))
    head.putalpha(m)

    # Composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head, (bx - cw // 2, by - ch // 2))
    return body, (center, major, minor, rx, ry, theta)

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
    bg.convert("RGB").save(os.path.join(OUT, f"v16_{tag}_f001.jpg"), quality=90)
    center, major, minor, rx, ry, theta = params
    print(f"{tag}: center=({center[0]:.0f},{center[1]:.0f}) theta={math.degrees(theta):.1f} r=({rx:.0f},{ry:.0f})")
print("done")
