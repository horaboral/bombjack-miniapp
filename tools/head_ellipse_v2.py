"""Head ellipse v2: extend the face oval up over the forehead/hair and down
to a bit of neck, then fit the rotated ellipse. Save the contour overlay and
the fitted-ellipse overlay for frame 1."""
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

# Extended head contour:
# - top: forehead/hair (landmarks 10, 6, 197, 195, 5, 45, 70, 63, 105)
# - sides: temples + cheeks (338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288)
# - jaw: (397, 365, 379, 378, 400, 377, 150, 136, 172, 58, 132, 93, 234)
# - neck: add 2 synthetic points below the jaw to extend down
HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]

def detect(path):
    res = det.detect(mp.Image.create_from_file(path))
    if not res.face_landmarks:
        return None
    W, H = Image.open(path).size
    lm = res.face_landmarks[0]
    pts = [(lm[i].x * W, lm[i].y * H) for i in HEAD_BASE]
    return np.array(pts, dtype=np.float64), W, H, lm

def extend_head(pts, W, H):
    """Extend the contour: push the top points up (forehead/hair) and the
    bottom points down (neck), and widen the sides slightly."""
    out = pts.copy()
    # Top: landmarks 0-8 (10, 6, 197, 195, 5, 45, 70, 63, 105) -> push up ~12%
    for i in range(9):
        out[i, 1] = max(0, out[i, 1] - 0.12 * H)
    # Bottom: landmarks 20-32 (397..234) -> push down ~8% for neck
    for i in range(20, len(out)):
        out[i, 1] = min(H, out[i, 1] + 0.08 * H)
    # Sides: widen ~5%
    cx = out[:, 0].mean()
    for i in range(9, 20):
        out[i, 0] = cx + (out[i, 0] - cx) * 1.05
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
    ry = float(np.percentile(np.abs(c @ major), 95) * 1.03)
    rx = float(np.percentile(np.abs(c @ minor), 95) * 1.03)
    return center, major, minor, rx, ry

for side in ("left", "right"):
    path = os.path.join(FACES, side, "f_001.png")
    img = Image.open(path).convert("RGB")
    W, H = img.size
    pts, W, H, lm = detect(path)
    if pts is None:
        print(side, "NO FACE")
        continue
    extended = extend_head(pts, W, H)
    center, major, minor, rx, ry = fit_ellipse(extended)
    angle = math.degrees(math.atan2(major[0], -major[1]))

    d = ImageDraw.Draw(img)
    # Draw the extended contour in green
    contour = [(int(p[0]), int(p[1])) for p in extended]
    d.line(contour + [contour[0]], fill=(0, 255, 0), width=2)
    # Draw the fitted ellipse (rotated) in red
    pad = int(max(rx, ry) * 0.7)
    cw, ch = W + 2*pad, H + 2*pad
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    dd.ellipse([pad+center[0]-rx, pad+center[1]-ry, pad+center[0]+rx, pad+center[1]+ry], outline=255, width=3)
    m = m.rotate(angle, center=(pad+center[0], pad+center[1]), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad+W, pad+H))
    # Overlay red where mask is set
    for y in range(H):
        for x in range(W):
            if m.getpixel((x, y)) > 0:
                d.point((x, y), fill=(255, 0, 0))
    img.save(os.path.join(OUT, f"headfit_{side}_f001.jpg"), quality=92)
    print(f"{side}: center=({center[0]:.0f},{center[1]:.0f}) angle={angle:.1f} r=({rx:.0f},{ry:.0f})")
print("done")
