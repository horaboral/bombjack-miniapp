"""Debug v15: check what the affine transform maps the canvas center to."""
import os, math
import numpy as np
import mediapipe as mp
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
OUT = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
             379, 378, 400, 377, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
             54, 103, 67, 109]

face_path = os.path.join(FACES, "left", "f_001.png")
img = Image.open(face_path).convert("RGBA")
W, H = img.size
res = det.detect(mp.Image.create_from_file(face_path))
lm = res.face_landmarks[0]
oval = np.array([(lm[i].x * W, lm[i].y * H) for i in FACE_OVAL])

pts = np.array(oval, dtype=np.float64)
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
ry = float(np.percentile(np.abs(c @ major), 95) * 1.02)
rx = float(np.percentile(np.abs(c @ minor), 95) * 1.02)

print(f"center: ({center[0]:.1f}, {center[1]:.1f})")
print(f"major axis: ({major[0]:.3f}, {major[1]:.3f})")
print(f"minor axis: ({minor[0]:.3f}, {minor[1]:.3f})")
print(f"rx={rx:.1f} ry={ry:.1f}")

# For the roach: head_target_h = 230
head_target_h = 230
out_ry = head_target_h / 2.0
out_rx = out_ry * (rx / ry)
scale = out_ry / ry
print(f"out_ry={out_ry:.1f} out_rx={out_rx:.1f} scale={scale:.3f}")

# Affine coefficients
a = scale * major[0]
b = scale * minor[0]
cc = center[0]
d = scale * major[1]
e = scale * minor[1]
f = center[1]

pad = int(out_ry * 0.15)
cw = int(2 * (out_rx + pad))
ch = int(2 * (out_ry + pad))
c2 = cc - a*(cw//2) - b*(ch//2)
f2 = f - d*(cw//2) - e*(ch//2)

print(f"canvas: {cw}x{ch}")
print(f"affine (a,b,c,d,e,f): {a:.4f},{b:.4f},{c2:.2f},{d:.4f},{e:.4f},{f2:.2f}")

# Where does canvas center map to in the source?
src_x = a*(cw//2) + b*(ch//2) + c2
src_y = d*(cw//2) + e*(ch//2) + f2
print(f"canvas center ({cw//2},{ch//2}) maps to source: ({src_x:.1f}, {src_y:.1f})")
print(f"source center is: ({center[0]:.1f}, {center[1]:.1f})")

# Save the raw transform output
head = img.transform((cw, ch), Image.AFFINE, (a, b, c2, d, e, f2), resample=Image.BILINEAR)
head.save(os.path.join(OUT, "v15_debug_head.png"))
print("saved v15_debug_head.png")
