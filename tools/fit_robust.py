"""Robust ellipse fit to the traced hand-drawn contours using PCA + radial
percentiles. Also measures the eye-line tilt from MediaPipe for the
upright rotation, and saves a debug overlay of the fitted ellipses."""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
RAW = os.path.join(WS, "assets", "raw", "raw_f001.png")
MARKED = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
OUT = os.path.join(WS, "tools")

img = Image.open(MARKED).convert("RGB")
arr = np.array(img, dtype=np.int16)
R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
red_mask = (R > 140) & (G < 110) & (B < 110) & (R - G > 60) & (R - B > 60)
blue_mask = (B > 120) & (R < 130) & (B - R > 40) & (B - G > 25)

def pca_fit(pts):
    center = pts.mean(axis=0)
    c = pts - center
    cov = np.cov(c.T)
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, np.argmax(evals)]
    minor = evecs[:, np.argmin(evals)]
    # major axis = long axis of the head; force it to point upward-ish
    proj_maj = c @ major
    proj_min = c @ minor
    ry = float(np.percentile(np.abs(proj_maj), 95))
    rx = float(np.percentile(np.abs(proj_min), 95))
    # rotation of major axis from vertical (degrees, CCW positive)
    theta = math.degrees(math.atan2(major[0], -major[1]))
    # normalize to [-90, 90]
    if theta > 90: theta -= 180
    if theta < -90: theta += 180
    return center, major, ry, rx, theta

# --- MediaPipe eye-line tilt on the raw frame ---
base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
res = det.detect(mp.Image.create_from_file(RAW))
W, H = Image.open(RAW).size

faces = res.face_landmarks
left_lm = None; right_lm = None
for lm in faces:
    if lm[1].x * W < W / 2:
        left_lm = lm
    else:
        right_lm = lm

def face_tilt(lm):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    return math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))

print(f"MediaPipe left face eye-line tilt: {face_tilt(left_lm):+.1f} deg")
print(f"MediaPipe right face eye-line tilt: {face_tilt(right_lm):+.1f} deg")

results = {}
overlay = img.copy()
od = ImageDraw.Draw(overlay)
for name, mask, col in [("left", red_mask, (255, 0, 0)), ("right", blue_mask, (0, 0, 255))]:
    pts = np.column_stack(np.nonzero(mask)[::-1]).astype(np.float64)
    center, major, ry, rx, theta = pca_fit(pts)
    t = face_tilt(left_lm if name == "left" else right_lm)
    results[name] = {
        "center": [float(center[0]), float(center[1])],
        "ry": float(ry), "rx": float(rx),
        "major_angle_from_vertical_deg": float(theta),
        "eye_tilt_deg": float(t),
    }
    print(f"{name}: center=({center[0]:.0f},{center[1]:.0f}) rx={rx:.0f} ry={ry:.0f} "
          f"major-from-vertical={theta:+.1f} eye_tilt={t:+.1f}")
    # draw fitted ellipse on overlay
    rad = math.radians(theta)
    a, b = ry, rx
    box = [center[0] - a, center[1] - b, center[0] + a, center[1] + b]
    od.ellipse(box, outline=col, width=3)
    od.ellipse(box, outline=(255, 255, 0), width=1)

with open(os.path.join(OUT, "baseline_ellipses.json"), "w") as f:
    json.dump(results, f, indent=2)
overlay.save(os.path.join(WS, "assets", "preview", "contour_fit_f001.jpg"), quality=90)
print("saved baseline_ellipses.json + contour_fit_f001.jpg")
