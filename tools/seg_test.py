"""Test MediaPipe legacy FaceMesh on one crop from each character."""
import mediapipe as mp
from PIL import Image
import numpy as np
import os

src = r"D:\dsh workspace\dsh test project\assets\faces"

for name in ("left", "right"):
    im = Image.open(os.path.join(src, name, "f_027.png")).convert("RGB")
    arr = np.array(im)
    mp_seg = mp.solutions.face_mesh
    with mp_seg.FaceMesh(static_image_mode=True, refine_landmarks=True,
                         max_num_faces=1, include_face_reflection=False) as fm:
        res = fm.process(arr)
    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0]
        xs = [p.x for p in lm.landmark]; ys = [p.y for p in lm.landmark]
        print(name, "facemesh bbox:", round(min(xs),3), round(min(ys),3),
              round(max(xs),3), round(max(ys),3), "n_lm:", len(lm.landmark))
    else:
        print(name, "NO FACE DETECTED")
