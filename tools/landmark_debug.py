"""Run FaceLandmarker on frame 1 of each character; draw candidate landmarks
on the image and print their pixel coords so we can identify indices."""
import os
import mediapipe as mp
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
model = os.path.join(WS, "tools", "face_landmarker.task")
out = os.path.join(WS, "assets", "preview")

base = mp.tasks.BaseOptions(model_asset_path=model)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=1)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

# candidate indices to label
CAND = {
    1: "noseTip", 4: "noseBase", 152: "chin", 61: "mouthL", 291: "mouthR",
    105: "mouthCtr", 33: "eyeLout", 133: "eyeLin", 362: "eyeRin", 263: "eyeRout",
    6: "glabella", 10: "upperLip", 178: "lowerLip",
}

for name in ("left", "right"):
    p = os.path.join(WS, "assets", "faces", name, "f_001.png")
    img = Image.open(p)
    mp_img = mp.Image.create_from_file(p)
    res = det.detect(mp_img)
    if not res.face_landmarks:
        print(name, "NO FACE")
        continue
    lm = res.face_landmarks[0]
    W, H = img.size
    debug = img.copy()
    d = ImageDraw.Draw(debug)
    print(f"== {name} ({W}x{H}) ==")
    for idx, label in CAND.items():
        x = int(lm[idx].x * W); y = int(lm[idx].y * H)
        d.ellipse([x-6, y-6, x+6, y+6], outline="red", width=2)
        d.text((x+7, y-8), label, fill="yellow")
        print(f"  {label:10s} idx{idx:4d}  ({x:4d},{y:4d})")
    debug.save(os.path.join(out, f"lm_{name}_f001.jpg"), quality=90)
    print("saved lm", name)
print("done")
