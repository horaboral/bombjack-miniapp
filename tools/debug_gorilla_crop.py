"""Save the face crop before compositing to see what's being pasted."""
import os, math, json
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

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
    if fx >= W / 2:
        lm = f
        break

e1x = (lm[33].x * W + lm[133].x * W) / 2
e1y = (lm[33].y * H + lm[133].y * H) / 2
e2x = (lm[362].x * W + lm[263].x * W) / 2
e2y = (lm[362].y * H + lm[263].y * H) / 2
emx = (e1x + e2x) / 2
emy = (e1y + e2y) / 2
print(f"right face eye_mid: ({emx:.1f}, {emy:.1f})")

bl = BASE["right"]
erx, ery = bl["rx"], bl["ry"]
cx, cy = 691, 443  # baseline center
print(f"crop: x=[{cx-erx:.0f},{cx+erx:.0f}] y=[{cy-ery:.0f},{cy+ery:.0f}]")
print(f"crop center: ({cx}, {cy})")
print(f"face eye_mid: ({emx:.1f}, {emy:.1f})")
print(f"offset from face center to crop center: ({cx-emx:.1f}, {cy-emy:.1f})")

# The face is at eye_mid, but the crop is centered on the baseline center.
# If the baseline center is offset from the actual face, the face will
# appear off-center in the crop.
# 
# The baseline was measured from a PREVIOUS frame where the face was at
# (691, 443). But the actual face in THIS frame is at (emx, emy).
# The offset (cx-emx, cy-emy) is how far the face is from the crop center.
#
# For the composite, the face should be at the CENTER of the crop.
# So the crop should be centered on the face, not the baseline.
#
# BUT: the baseline center is the center of the CONTOUR (the white ellipse
# the user drew), which is slightly below the eyes (it includes the chin).
# The face should be positioned so that the CONTOUR center aligns with the
# body ellipse center.
#
# So the correct approach:
# 1. Crop centered on the CONTOUR center (691, 443) -- this is correct.
# 2. The face will be slightly above the crop center (eyes are above chin).
# 3. When we paste at the body ellipse center, the face will be slightly
#    above the body ellipse center, which is correct (the face should sit
#    in the upper part of the ellipse, with the chin at the bottom).
#
# The issue might be that the face is too small relative to the crop,
# so when scaled to fit the body ellipse, there's too much padding.

# Let's check: the face width (eyes to eyes) vs the crop width
eye_dist = math.sqrt((e2x-e1x)**2 + (e2y-e1y)**2)
print(f"\neye distance: {eye_dist:.1f} px")
print(f"crop width: {2*erx:.1f} px")
print(f"crop height: {2*ery:.1f} px")
print(f"eye_dist / crop_width: {eye_dist/(2*erx):.3f}")

# The face should fill most of the crop. If eye_dist is much smaller
# than crop_width, there's too much padding.
