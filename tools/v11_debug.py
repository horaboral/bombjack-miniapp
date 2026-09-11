"""Debug: save the cropped face + ellipse mask to see what's happening."""
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

face_path = os.path.join(FACES, "left", "f_001.png")
img = Image.open(face_path)
W, H = img.size
res = det.detect(mp.Image.create_from_file(face_path))
lm = res.face_landmarks[0]
pts = {}
for idx, label in [(1,"noseTip"),(4,"noseBase"),(152,"chin"),
                    (33,"eyeLout"),(133,"eyeLin"),(263,"eyeRout"),(362,"eyeRin"),
                    (61,"mouthL"),(291,"mouthR"),(6,"glabella"),(178,"lowerLip")]:
    pts[label] = (lm[idx].x * W, lm[idx].y * H)

eyeL = np.array([(pts["eyeLout"][0]+pts["eyeLin"][0])/2, (pts["eyeLout"][1]+pts["eyeLin"][1])/2])
eyeR = np.array([(pts["eyeRin"][0]+pts["eyeRout"][0])/2, (pts["eyeRin"][1]+pts["eyeRout"][1])/2])
eyeMid = (eyeL + eyeR) / 2
noseTip = np.array(pts["noseTip"])
chin = np.array(pts["chin"])
glabella = np.array(pts["glabella"])
v = chin - eyeMid
angle = math.degrees(math.atan2(v[0], -v[1]))
center_full = (glabella + chin) / 2 + (chin - glabella) * 0.15
interocular = np.linalg.norm(eyeR - eyeL)
ry_full = np.linalg.norm(chin - eyeMid) * 0.70
rx_full = interocular * 0.85

top = glabella[1] - 0.4 * (glabella[1] - eyeMid[1])
bottom = chin[1] + 0.4 * (chin[1] - noseTip[1])
left = eyeMid[0] - interocular * 0.75
right = eyeMid[0] + interocular * 0.75
w = right - left
h = bottom - top
size = max(w, h) * 1.1
cx_full = (left + right) / 2
cy_full = (top + bottom) / 2
crop_x = int(cx_full - size / 2)
crop_y = int(cy_full - size / 2)
crop_w = int(size)
crop_h = int(size)
crop_x = max(0, min(crop_x, W - crop_w))
crop_y = max(0, min(crop_y, H - crop_h))

ex = int(center_full[0] - crop_x)
ey = int(center_full[1] - crop_y)
rx = int(rx_full)
ry = int(ry_full)

print(f"Landmarks (full 400x400):")
for k, v in pts.items():
    print(f"  {k}: ({v[0]:.0f}, {v[1]:.0f})")
print(f"eyeMid: ({eyeMid[0]:.0f},{eyeMid[1]:.0f})")
print(f"center_full: ({center_full[0]:.0f},{center_full[1]:.0f})")
print(f"angle: {angle:.1f}")
print(f"rx,ry: {rx},{ry}")
print(f"crop: ({crop_x},{crop_y}) {crop_w}x{crop_h}")
print(f"ellipse in crop: ({ex},{ey})")

# Save the crop with ellipse drawn on it
face_crop = img.crop((crop_x, crop_y, crop_x+crop_w, crop_y+crop_h)).convert("RGB")
d = ImageDraw.Draw(face_crop)
# Draw the ellipse
pad = int(max(rx, ry) * 0.7)
cw, ch = crop_w + 2*pad, crop_h + 2*pad
m = Image.new("L", (cw, ch), 0)
dd = ImageDraw.Draw(m)
dd.ellipse([pad+ex-rx, pad+ey-ry, pad+ex+rx, pad+ey+ry], outline=255, width=3)
m = m.rotate(angle, center=(pad+ex, pad+ey), resample=Image.BICUBIC)
m = m.crop((pad, pad, pad+crop_w, pad+crop_h))
# Overlay ellipse outline on the crop
overlay = face_crop.copy()
od = ImageDraw.Draw(overlay)
# Draw ellipse using the mask as a guide
for y in range(crop_h):
    for x in range(crop_w):
        if m.getpixel((x, y)) > 0:
            od.point((x, y), fill=(255, 0, 0))
overlay.save(os.path.join(OUT, "v11_debug_crop_ellipse.png"))
face_crop.save(os.path.join(OUT, "v11_debug_crop.png"))
print("saved debug images")
