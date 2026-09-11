"""Per-frame full-head upright compositor v15.
- Fits the ellipse to the FACE OVAL landmarks per frame (orientation + size)
- Uses an affine transform to map the tilted head directly to a vertical,
  upright head in output space (no rotate-then-crop)
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
    pts = np.array(oval_pts, dtype=np.float64)
    center = pts.mean(axis=0)
    c = pts - center
    cov = np.cov(c.T)
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, np.argmax(evals)]
    minor = evecs[:, np.argmin(evals)]
    # Make major point "down" (positive y in image space)
    if major[1] < 0:
        major = -major
    # Orthogonalize minor to major
    minor = minor - (minor @ major) * major
    minor /= np.linalg.norm(minor)
    # Radii from 95th percentile projected extents
    ry = float(np.percentile(np.abs(c @ major), 95) * 1.02)
    rx = float(np.percentile(np.abs(c @ minor), 95) * 1.02)
    return (center, major, minor, rx, ry)

def build_frame(face_name, body_path, body_head_xy, head_target_h, frame):
    face_path = os.path.join(FACES, face_name, f"f_{frame:03d}.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    oval, W, H = detect(face_path)
    if oval is None:
        return None, None

    center, major, minor, rx, ry = fit_ellipse(oval)
    # Output: vertical ellipse, height = head_target_h, width = head_target_h * (rx/ry)
    out_ry = head_target_h / 2.0
    out_rx = out_ry * (rx / ry)
    scale = out_ry / ry

    # Affine: out(x,y) = A * in(x,y) + t
    # We want: in = center + major*u*ry + minor*v*rx  ->  out = (u*rx_out, v*ry_out)
    # So: in = center + [major*ry, minor*rx] * [u; v]
    #     out = [rx_out, 0; 0, ry_out] * [u; v]
    # Invert: [u;v] = [1/rx_out, 0; 0, 1/ry_out] * out
    # in = center + [major*ry, minor*rx] * [1/rx_out, 0; 0, 1/ry_out] * out
    # in = center + [major*ry/rx_out, minor*rx/ry_out] * out
    #     = center + [major*scale, minor*scale] * out   (since scale=ry/ry_out=rx/rx_out)
    # in(x,y) = center + scale * (major * out_x + minor * out_y)
    # in_x = center_x + scale * (major_x * out_x + minor_x * out_y)
    # in_y = center_y + scale * (major_y * out_x + minor_y * out_y)
    # PIL affine: out[x,y] = in[a*x+b*y+c, d*x+e*y+f]
    a = scale * major[0]
    b = scale * minor[0]
    c = center[0]
    d = scale * major[1]
    e = scale * minor[1]
    f = center[1]

    # Output canvas: vertical ellipse + margin
    pad = int(out_ry * 0.15)
    cw = int(2 * (out_rx + pad))
    ch = int(2 * (out_ry + pad))
    # Shift so ellipse center is at canvas center (cw/2, ch/2)
    # out_local = out - (cw/2, ch/2)
    # in = center + scale * (major * out_local_x + minor * out_local_y)
    a2 = a; b2 = b
    c2 = c - a*(cw//2) - b*(ch//2)
    d2 = d; e2 = e
    f2 = f - d*(cw//2) - e*(ch//2)

    head = img.transform((cw, ch), Image.AFFINE,
                          (a2, b2, c2, d2, e2, f2), resample=Image.BILINEAR)

    # Vertical ellipse mask (sharp, 1px feather)
    erx = int(out_rx); ery = int(out_ry)
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    dd.ellipse([cw//2 - erx, ch//2 - ery, cw//2 + erx, ch//2 + ery], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1))
    head.putalpha(m)

    # Composite onto headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head, (bx - cw // 2, by - ch // 2))
    return body, (center, rx, ry)

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
    bg.convert("RGB").save(os.path.join(OUT, f"v15_{tag}_f001.jpg"), quality=90)
    center, rx, ry = params
    print(f"{tag}: center=({center[0]:.0f},{center[1]:.0f}) r=({rx:.0f},{ry:.0f})")
print("done")
