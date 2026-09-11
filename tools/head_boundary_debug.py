"""Draw head-boundary landmarks (jaw, cheek, hairline) on frame 1 crops."""
import os
import mediapipe as mp
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
OUT = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

# Jaw contour: 234, 93, 132, 58, 172, 136, 150, 149, 377, 400, 378, 379, 365, 397
# Cheek/hairline: 10, 338, 297, 268, 269, 270, 0, 26, 1, 6, 197, 195, 5, 45, 70, 63, 105
# Hairline approx: 10, 338, 297, 268, 269, 270, 0, 26, 1, 6, 197, 195, 5, 45, 70, 63, 105
JAW = [234, 93, 132, 58, 172, 136, 150, 149, 377, 400, 378, 379, 365, 397]
HAIR = [10, 338, 297, 268, 269, 270, 0, 26, 1, 6, 197, 195, 5, 45, 70, 63, 105]
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
             379, 378, 400, 377, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
             54, 103, 67, 109]

for side in ("left", "right"):
    path = os.path.join(FACES, side, "f_001.png")
    img = Image.open(path).convert("RGB")
    W, H = img.size
    res = det.detect(mp.Image.create_from_file(path))
    lm = res.face_landmarks[0]
    d = ImageDraw.Draw(img)
    def pt(idx, color, r=3):
        p = (lm[idx].x * W, lm[idx].y * H)
        d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=color)
        return p
    # jaw in red
    jaw_pts = [pt(i, (255, 0, 0)) for i in JAW]
    d.line(jaw_pts + [jaw_pts[0]], fill=(255, 0, 0), width=2)
    # hairline in blue
    hair_pts = [pt(i, (0, 0, 255), 2) for i in HAIR]
    d.line(hair_pts + [hair_pts[0]], fill=(0, 0, 255), width=2)
    # face oval in green
    oval_pts = [pt(i, (0, 255, 0), 2) for i in FACE_OVAL]
    d.line(oval_pts + [oval_pts[0]], fill=(0, 255, 0), width=2)
    # nose tip
    pt(1, (255, 255, 0), 4)
    img.save(os.path.join(OUT, f"head_{side}_f001.jpg"), quality=92)
    # print jaw extent
    import numpy as np
    jaw = np.array(jaw_pts)
    hair = np.array(hair_pts)
    print(f"{side}: jaw y range {jaw[:,1].min():.0f}-{jaw[:,1].max():.0f}, "
          f"x {jaw[:,0].min():.0f}-{jaw[:,0].max():.0f}; "
          f"hair y {hair[:,1].min():.0f}-{hair[:,1].max():.0f}, "
          f"x {hair[:,0].min():.0f}-{hair[:,0].max():.0f}")
print("done")
