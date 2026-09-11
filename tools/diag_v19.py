"""Diagnose: draw the MediaPipe head contour, the baseline ellipse, and the
eye centers on the raw crop to see where everything lands."""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]

for side in ("left", "right"):
    face_path = os.path.join(FACES, side, "f_001.png")
    img = Image.open(face_path).convert("RGB")
    W, H = img.size
    res = det.detect(mp.Image.create_from_file(face_path))
    if not res.face_landmarks:
        print(f"{side}: NO FACE"); continue
    lm = res.face_landmarks[0]
    d = ImageDraw.Draw(img)
    # head contour
    pts = [(lm[i].x * W, lm[i].y * H) for i in HEAD_BASE]
    d.line(pts + [pts[0]], fill=(0, 255, 0), width=2)
    # head centroid
    head = np.array(pts)
    hc = (head[:, 0].mean(), head[:, 1].mean())
    d.ellipse([hc[0] - 5, hc[1] - 5, hc[0] + 5, hc[1] + 5], fill=(255, 0, 255))
    # eye centers
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    d.ellipse([e1[0] - 4, e1[1] - 4, e1[0] + 4, e1[1] + 4], fill=(255, 255, 0))
    d.ellipse([e2[0] - 4, e2[1] - 4, e2[0] + 4, e2[1] + 4], fill=(255, 255, 0))
    d.line([e1, e2], fill=(255, 255, 0), width=2)
    # baseline ellipse (user contour shape, centered on head centroid)
    bl = BASE[side]
    s = W / 800.0
    erx, ery = bl["rx"] * s, bl["ry"] * s
    tilt = math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))
    d.ellipse([hc[0] - erx, hc[1] - ery, hc[0] + erx, hc[1] + ery],
              outline=(0, 200, 255), width=2)
    print(f"{side}: head_c={hc[0]:.0f},{hc[1]:.0f} eye1={e1[0]:.0f},{e1[1]:.0f} "
          f"eye2={e2[0]:.0f},{e2[1]:.0f} tilt={tilt:+.1f} er=({erx:.0f},{ery:.0f})")
    out = os.path.join(WS, "assets", "preview", f"diag_{side}_f001.png")
    img.save(out)
    print(f"  saved {out}")
print("done")
