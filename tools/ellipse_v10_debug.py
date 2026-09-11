"""Debug: check the affine transform output before masking."""
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

face_path = os.path.join(FACES, "left", "f_001.png")
img = Image.open(face_path).convert("RGBA")
W, H = img.size
res = det.detect(mp.Image.create_from_file(face_path))
lm = res.face_landmarks[0]
pts = {}
for idx, label in [(1,"noseTip"),(4,"noseBase"),(152,"chin"),
                    (33,"eyeLout"),(133,"eyeLin"),(263,"eyeRout"),(362,"eyeRin"),
                    (61,"mouthL"),(291,"mouthR"),(178,"lowerLip")]:
    pts[label] = (lm[idx].x * W, lm[idx].y * H)

eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2, (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2, (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
eyeMid = (eyeL + eyeR) / 2
noseTip = np.array(pts["noseTip"])
chin = np.array(pts["chin"])
v = chin - eyeMid
angle = math.degrees(math.atan2(v[0], -v[1]))
center = (noseTip + chin) / 2 + (chin - noseTip) * 0.20
interocular = np.linalg.norm(eyeR - eyeL)
ry = np.linalg.norm(chin - eyeMid) * 0.80
rx = interocular * 0.92
fcx, fcy = center

target_ry = 105
scale = target_ry / ry
target_rx = rx * scale
bfx, bfy = 179, 168

ca, sa = math.cos(math.radians(-angle)), math.sin(math.radians(-angle))
a = ca / scale; b = sa / scale
d = -sa / scale; e = ca / scale
c = fcx - a*bfx - b*bfy
f = fcy - d*bfx - e*bfy

cw = int(2 * (target_rx + 20))
ch = int(2 * (target_ry + 20))
c2 = c - a*(cw//2) - b*(ch//2)
f2 = f - d*(cw//2) - e*(ch//2)

print(f"face center: ({fcx:.0f},{fcy:.0f})")
print(f"angle: {angle:.1f}")
print(f"face rx,ry: {rx:.0f},{ry:.0f}")
print(f"scale: {scale:.3f}")
print(f"target rx,ry: {target_rx:.0f},{target_ry:.0f}")
print(f"canvas: {cw}x{ch}")
print(f"affine (a,b,c,d,e,f): {a:.4f},{b:.4f},{c:.2f},{d:.4f},{e:.4f},{f2:.2f}")

# Test: what does the transform map the canvas center to?
# out[cw/2, ch/2] = in[a*cw/2 + b*ch/2 + c2, d*cw/2 + e*ch/2 + f2]
src_x = a*(cw//2) + b*(ch//2) + c2
src_y = d*(cw//2) + e*(ch//2) + f2
print(f"canvas center maps to face pixel: ({src_x:.0f},{src_y:.0f})")
print(f"face center is at: ({fcx:.0f},{fcy:.0f})")

# Save the unmasked transform result
face_canvas = img.transform((cw, ch), Image.AFFINE, (a, b, c2, d, e, f2), resample=Image.BILINEAR)
face_canvas.save(os.path.join(OUT, "v10_debug_transform.png"))
print("saved v10_debug_transform.png")
