"""Debug: show where the face lands vs the white ellipse on frame 1."""
import os, math, json
import mediapipe as mp
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

raw = Image.open(os.path.join(WS, "assets", "raw", "raw_f001.png")).convert("RGBA")
W, H = raw.size

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
res = det.detect(mp.Image.create_from_file(os.path.join(WS, "assets", "raw", "raw_f001.png")))

for f in res.face_landmarks:
    fx = f[1].x * W
    e1x = (f[33].x * W + f[133].x * W) / 2
    e1y = (f[33].y * H + f[133].y * H) / 2
    e2x = (f[362].x * W + f[263].x * W) / 2
    e2y = (f[362].y * H + f[263].y * H) / 2
    emx = (e1x + e2x) / 2
    emy = (e1y + e2y) / 2
    side = "RIGHT" if fx >= W / 2 else "LEFT"
    print(f"{side}: nose_x={fx:.0f} eye_mid=({emx:.1f},{emy:.1f})")

bl = BASE["right"]
erx, ery = bl["rx"], bl["ry"]
off_x, off_y = 691 - emx, 443 - emy
cx, cy = emx + off_x, emy + off_y
print(f"\nbaseline right: center=({cx:.1f},{cy:.1f}) erx={erx} ery={ery}")
print(f"crop: x=[{cx-erx:.0f},{cx+erx:.0f}] y=[{cy-ery:.0f},{cy+ery:.0f}]")
print(f"crop center = ({cx:.1f},{cy:.1f})")

# Body ellipse
g_cx, g_cy = 388.5, 235.5
g_rx, g_ry = 81.5, 103.5
print(f"\nbody ellipse: center=({g_cx},{g_cy}) rx={g_rx} ry={g_ry}")
print(f"body ellipse bbox: x=[{g_cx-g_rx:.0f},{g_cx+g_rx:.0f}] y=[{g_cy-g_ry:.0f},{g_cy+g_ry:.0f}]")

# After scaling: crop is 2*erx x 2*ery = 480 x 566
# target: 163 x 207
# scale = max(163/480, 207/566) = max(0.3396, 0.3657) = 0.3657
crop_w, crop_h = int(2*erx), int(2*ery)
target_w, target_h = int(2*g_rx), int(2*g_ry)
scale = max(target_w / crop_w, target_h / crop_h)
new_w = int(crop_w * scale)
new_h = int(crop_h * scale)
px = int(g_cx - new_w / 2)
py = int(g_cy - new_h / 2)
print(f"\nscale={scale:.4f} new={new_w}x{new_h}")
print(f"paste at ({px},{py}), covers x=[{px},{px+new_w}] y=[{py},{py+new_h}]")
print(f"face center in body coords: ({px + new_w/2:.1f}, {py + new_h/2:.1f})")
print(f"body ellipse center: ({g_cx}, {g_cy})")
