"""Retry detection on the 3 failed roach frames with num_faces=2 and
relaxed thresholds. If still failing, keep the fallback copies."""
import os, math, time
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
BODIES = os.path.join(WS, "assets", "bodies")
OUT = os.path.join(WS, "assets", "final")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(
    base_options=base, num_faces=2, min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]
EYE_L_OUT, EYE_L_IN = 33, 133
EYE_R_IN, EYE_R_OUT = 362, 263

def detect(path):
    res = det.detect(mp.Image.create_from_file(path))
    if not res.face_landmarks:
        return None
    # Pick the face with the most central nose tip
    W, H = Image.open(path).size
    best = None; best_score = 1e9
    for lm in res.face_landmarks:
        nx, ny = lm[1].x * W, lm[1].y * H
        score = (nx - W/2)**2 + (ny - H/2)**2
        if score < best_score:
            best_score = score; best = lm
    lm = best
    head = np.array([(lm[i].x * W, lm[i].y * H) for i in HEAD_BASE], dtype=np.float64)
    eye_l = ((lm[EYE_L_OUT].x * W + lm[EYE_L_IN].x * W) / 2,
             (lm[EYE_L_OUT].y * H + lm[EYE_L_IN].y * H) / 2)
    eye_r = ((lm[EYE_R_IN].x * W + lm[EYE_R_OUT].x * W) / 2,
             (lm[EYE_R_IN].y * H + lm[EYE_R_OUT].y * H) / 2)
    return head, eye_l, eye_r, W, H

def extend_head(pts, W, H):
    out = pts.copy()
    for i in range(9):
        out[i, 1] = max(0, out[i, 1] - 0.18 * H)
    for i in range(20, len(out)):
        out[i, 1] = min(H, out[i, 1] + 0.08 * H)
    cx = out[:, 0].mean()
    for i in range(9, 20):
        out[i, 0] = cx + (out[i, 0] - cx) * 1.06
    return out

def fit_ellipse(pts):
    center = pts.mean(axis=0)
    c = pts - center
    cov = np.cov(c.T)
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, np.argmax(evals)]
    minor = evecs[:, np.argmin(evals)]
    if major[1] < 0:
        major = -major
    minor = minor - (minor @ major) * major
    minor /= np.linalg.norm(minor)
    ry = float(np.percentile(np.abs(c @ major), 92) * 0.98)
    rx = float(np.percentile(np.abs(c @ minor), 92) * 0.98)
    return center, major, minor, rx, ry

def build_frame(face_path, body_path, body_head_xy, head_target_h):
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    det_result = detect(face_path)
    if det_result is None:
        return None
    head, eye_l, eye_r, W, H = det_result
    extended = extend_head(head, W, H)
    center, major, minor, rx, ry = fit_ellipse(extended)
    dx = eye_r[0] - eye_l[0]; dy = eye_r[1] - eye_l[1]
    tilt = math.degrees(math.atan2(dy, dx))

    angle = math.degrees(math.atan2(major[0], major[1]))
    pad = int(max(rx, ry) * 1.5)
    cw, ch = W + 2 * pad, H + 2 * pad
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    cx, cy = pad + center[0], pad + center[1]
    dd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    m = m.rotate(angle, center=(cx, cy), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad + W, pad + H))
    img.putalpha(m)

    img = img.rotate(-tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)

    rad = math.radians(-tilt)
    ddx = center[0] - W / 2
    ddy = center[1] - H / 2
    new_cx = ddx * math.cos(rad) - ddy * math.sin(rad) + W / 2
    new_cy = ddx * math.sin(rad) + ddy * math.cos(rad) + W / 2

    margin = int(max(rx, ry) * 0.15)
    crop_w = int(2 * (rx + margin))
    crop_h = int(2 * (ry + margin))
    x0 = int(new_cx - crop_w / 2)
    y0 = int(new_cy - crop_h / 2)
    px = max(0, -x0); py = max(0, -y0)
    nx = max(0, x0 + crop_w - W); ny = max(0, y0 + crop_h - H)
    if px or py or nx or ny:
        big = Image.new("RGBA", (W + px + nx, H + py + ny), (0, 0, 0, 0))
        big.paste(img, (px, py))
        x0 += px; y0 += py
        img = big
    head_crop = img.crop((x0, y0, x0 + crop_w, y0 + crop_h))

    erx = int(rx); ery = int(ry)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erx, crop_h // 2 - ery,
                 crop_w // 2 + erx, crop_h // 2 + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    scale = (head_target_h / 2.0) / ry
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    return body

ROACH_BODY = os.path.join(BODIES, "cockroach_full.png")
for fr in (17, 22, 23):
    face_path = os.path.join(FACES, "left", f"f_{fr:03d}.png")
    body_img = build_frame(face_path, ROACH_BODY, (179, 175), 230)
    if body_img is None:
        print(f"frame {fr}: STILL NO FACE (keeping fallback)")
    else:
        body_img.save(os.path.join(OUT, "roach", f"f_{fr:03d}.png"))
        print(f"frame {fr}: recovered")
print("done")
