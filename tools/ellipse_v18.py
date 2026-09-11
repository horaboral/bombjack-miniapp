"""v18: fix rotation direction (CW tilt -> CCW rotate), extend contour up 0.25H,
down 0.10H, composite onto original (full) bodies to eliminate the blurred
rectangle. Frame 1 preview only."""
import os, math
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
BODIES = os.path.join(WS, "assets", "bodies")
PREVIEW = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
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
        out[i, 1] = max(0, out[i, 1] - 0.25 * H)
    for i in range(20, len(out)):
        out[i, 1] = min(H, out[i, 1] + 0.10 * H)
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

def eye_tilt(eye_l, eye_r):
    dx = eye_r[0] - eye_l[0]
    dy = eye_r[1] - eye_l[1]
    return math.degrees(math.atan2(dy, dx))

def build_frame(face_path, body_path, body_head_xy, head_target_h):
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size
    det_result = detect(face_path)
    if det_result is None:
        return None
    head, eye_l, eye_r, W, H = det_result
    extended = extend_head(head, W, H)
    center, major, minor, rx, ry = fit_ellipse(extended)
    tilt = eye_tilt(eye_l, eye_r)

    # 1) source-space ellipse mask (kills the crop square)
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

    # 2) upright: tilt>0 = face tilted CW -> rotate CCW by +tilt (PIL CCW positive)
    img = img.rotate(tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)

    rad = math.radians(tilt)
    dx = center[0] - W / 2
    dy = center[1] - H / 2
    new_cx = dx * math.cos(rad) - dy * math.sin(rad) + W / 2
    new_cy = dx * math.sin(rad) + dy * math.cos(rad) + H / 2

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

    # 3) vertical tight ellipse
    erx = int(rx); ery = int(ry)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erx, crop_h // 2 - ery,
                 crop_w // 2 + erx, crop_h // 2 + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    # 4) scale so 2*ry -> head_target_h
    scale = (head_target_h / 2.0) / ry
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) composite onto original (full) body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    return body

for tag, side, body, xy, th in [
    ("roach", "left", os.path.join(BODIES, "cockroach_full.png"), (179, 175), 230),
    ("gorilla", "right", os.path.join(BODIES, "gorilla_full.png"), (150, 75), 110),
]:
    face_path = os.path.join(FACES, side, "f_001.png")
    img = build_frame(face_path, body, xy, th)
    if img is None:
        print(f"{tag}: NO FACE")
        continue
    out = os.path.join(PREVIEW, f"v18_{tag}_f001.png")
    img.save(out)
    print(f"saved {out} tilt={eye_tilt(*detect(face_path)[1:3]):+.1f}")
print("done")
