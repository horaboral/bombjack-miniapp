"""Per-frame full-head rotated-ellipse compositor v14.
- Fits the ellipse to the FACE OVAL landmarks (jaw + hairline) per frame
- Rotates the face crop upright (eye-line based) before compositing
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

# MediaPipe face oval contour (468-point mesh)
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
             379, 378, 400, 377, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
             54, 103, 67, 109]

def detect(path):
    res = det.detect(mp.Image.create_from_file(path))
    if not res.face_landmarks:
        return None
    W, H = Image.open(path).size
    lm = res.face_landmarks[0]
    return np.array([(lm[i].x * W, lm[i].y * H) for i in FACE_OVAL]), W, H

def fit_ellipse(oval_pts):
    """Fit a rotated ellipse to the head-contour points.
    Returns (cx, cy, angle_deg, rx, ry) using the covariance/PCA method:
    - center = mean of points
    - major/minor axes from eigenvectors of the covariance
    - radii from projected extents along each axis
    """
    pts = np.array(oval_pts, dtype=np.float64)
    center = pts.mean(axis=0)
    c = pts - center
    cov = np.cov(c.T)
    evals, evecs = np.linalg.eigh(cov)
    # evecs columns are eigenvectors; largest eval = major axis
    major = evecs[:, np.argmax(evals)]
    minor = evecs[:, np.argmin(evals)]
    # Angle of major axis from vertical (0 = upright)
    angle = math.degrees(math.atan2(major[0], -major[1]))
    # Radii: max projected distance along each axis
    proj_major = np.abs(c @ major).max()
    proj_minor = np.abs(c @ minor).max()
    # Use 95th percentile to avoid outliers, with a small margin
    rx = np.percentile(np.abs(c @ minor), 95) * 1.05  # width (minor axis)
    ry = np.percentile(np.abs(c @ major), 95) * 1.05  # height (major axis)
    return (center[0], center[1], angle, float(rx), float(ry))

def build_frame(face_name, body_path, body_head_xy, head_target_h, frame, upright=True):
    """head_target_h: desired full height (2*ry) of the head ellipse in body pixels."""
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    oval, W, H = detect(face_path)
    if oval is None:
        return None, None

    cx, cy, angle, rx, ry = fit_ellipse(oval)
    scale = (head_target_h / 2.0) / ry

    if upright:
        # Rotate the whole face crop so the face is vertical.
        # The ellipse (drawn vertical in canvas space) must stay aligned with
        # the face after rotation, so rotate by +angle (PIL rotates CW for
        # positive angles).
        img = img.rotate(-angle, center=(cx, cy), resample=Image.BICUBIC, expand=False)
        # After this rotation the face major axis is vertical in image space.

    # Build a canvas that contains the full uprighted ellipse + margin
    pad = int(max(rx, ry) * 0.15)
    cw = int(2 * (rx + pad))
    ch = int(2 * (ry + pad))
    # Crop the rotated image around the ellipse center
    x0 = int(cx - cw / 2)
    y0 = int(cy - ch / 2)
    # Pad the image with transparent black so the crop doesn't go out of bounds
    if x0 < 0 or y0 < 0 or x0 + cw > W or y0 + ch > H:
        px = max(0, -x0); py = max(0, -y0)
        nx = max(0, x0 + cw - W); ny = max(0, y0 + ch - H)
        big = Image.new("RGBA", (W + px + nx, H + py + ny), (0, 0, 0, 0))
        big.paste(img, (px, py))
        x0 += px; y0 += py
        img = big
    head = img.crop((x0, y0, x0 + cw, y0 + ch))

    # Ellipse mask in canvas space (center = canvas center, angle = 0 if upright)
    erx = int(rx); ery = int(ry)
    m = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([cw//2 - erx, ch//2 - ery, cw//2 + erx, ch//2 + ery], fill=255)
    if not upright:
        m = m.rotate(angle, center=(cw//2, ch//2), resample=Image.BICUBIC)
    m = m.filter(ImageFilter.GaussianBlur(1))
    head.putalpha(m)

    # Scale to body size
    new_w = int(cw * scale)
    new_h = int(ch * scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)

    # Composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head, (bx - new_w // 2, by - new_h // 2))
    return body, (cx, cy, angle, rx, ry, scale)

# Parameters
ROACH_BODY = os.path.join(BODIES, "cockroach_headless.png")
GOR_BODY = os.path.join(BODIES, "gorilla_headless.png")

# Head target heights (body px): cockroach 358x734 -> ~230px tall head; gorilla 300x232 -> ~110px
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
    bg.convert("RGB").save(os.path.join(OUT, f"v14_{tag}_f001.jpg"), quality=90)
    cx, cy, angle, rx, ry, sc = params
    print(f"{tag}: center=({cx:.0f},{cy:.0f}) angle={angle:.1f} r=({rx:.0f},{ry:.0f}) scale={sc:.3f}")
print("done")
