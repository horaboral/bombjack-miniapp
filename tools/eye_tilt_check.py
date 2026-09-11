"""Check eye-line tilt per side on frames 1, 17, 37 (left + right).
Eye-line angle tells us the actual face tilt in image space."""
import os, math
import mediapipe as mp
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

for side in ("left", "right"):
    for fr in (1, 17, 37, 53):
        p = os.path.join(FACES, side, f"f_{fr:03d}.png")
        res = det.detect(mp.Image.create_from_file(p))
        if not res.face_landmarks:
            print(side, fr, "NO FACE")
            continue
        lm = res.face_landmarks[0]
        W, H = Image.open(p).size
        def P(i): return (lm[i].x * W, lm[i].y * H)
        eyeLout, eyeLin = P(33), P(133)
        eyeRin, eyeRout = P(362), P(263)
        L = (eyeLout[0] + eyeLin[0]) / 2, (eyeLout[1] + eyeLin[1]) / 2
        R = (eyeRin[0] + eyeRout[0]) / 2, (eyeRin[1] + eyeRout[1]) / 2
        dx, dy = R[0] - L[0], R[1] - L[1]
        ang = math.degrees(math.atan2(dy, dx))  # 0 = horizontal (face upright)
        print(f"{side} f{fr:03d}: eyeL=({L[0]:.0f},{L[1]:.0f}) eyeR=({R[0]:.0f},{R[1]:.0f}) tilt={ang:+.1f} deg (0=upright)")
print("done")
