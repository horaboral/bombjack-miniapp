"""Debug: save the raw transform output before masking for v16."""
import os, math
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
OUT = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

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

face_path = os.path.join(FACES, "left", "f_001.png")
img = Image.open(face_path).convert("RGBA")
W, H = img.size
pts, W, H = detect(face_path)
extended = extend_head(pts, W, H)
center, major, minor, rx, ry = fit_ellipse(extended)

head_target_h = 230
out_ry = head_target_h / 2.0
out_rx = out_ry * (rx / ry)
scale = out_ry / ry
theta = math.atan2(major[0], major[1])
ct, st = math.cos(theta), math.sin(theta)

pad = int(out_ry * 0.15)
cw = int(2 * (out_rx + pad))
ch = int(2 * (out_ry + pad))
ccx, ccy = cw // 2, ch // 2

a = ct / scale
b = st / scale
d = -st / scale
e = ct / scale
c = center[0] - a * ccx - b * ccy
f = center[1] - d * ccx - e * ccy

head = img.transform((cw, ch), Image.AFFINE, (a, b, c, d, e, f), resample=Image.BILINEAR)
# Save raw (no mask) to see what pixels are actually there
head.save(os.path.join(OUT, "v16_debug_raw.png"))
# Also draw the ellipse outline on it
d2 = ImageDraw.Draw(head)
erx = int(out_rx); ery = int(out_ry)
d2.ellipse([ccx - erx, ccy - ery, ccx + erx, ccy + ery], outline=(255, 0, 0), width=2)
head.save(os.path.join(OUT, "v16_debug_ellipse.png"))
print(f"center=({center[0]:.0f},{center[1]:.0f}) theta={math.degrees(theta):.1f} r=({rx:.0f},{ry:.0f})")
print(f"out: {cw}x{ch} erx={erx} ery={ery}")
print("saved v16_debug_raw.png and v16_debug_ellipse.png")
