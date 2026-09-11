"""v19: baseline ellipse from user-drawn contours (tools/baseline_ellipses.json).
Frame-1 validation: left face -> headless cockroach, right face -> headless gorilla.
- Source-space ellipse mask (user baseline shape, rotated to head orientation)
- Upright rotation: +eye_tilt (CCW in PIL) to cancel the CW eye-line tilt
- Vertical tight ellipse, scale to head target, composite onto user headless bodies
Outputs: assets/preview/v19_roach_f001.png, v19_gorilla_f001.png,
         v19_debug_mask_left.png (mask alone, to verify shape)
"""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
FACES = os.path.join(WS, "assets", "faces")
BODIES = os.path.join(WS, "assets", "bodies")
PREVIEW = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

HEAD_BASE = [10, 6, 197, 195, 5, 45, 70, 63, 105, 338, 297, 332, 284, 251,
             389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 150,
             136, 172, 58, 132, 93, 234]

def eye_tilt_of(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    return math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))

def build(tag, side, body_path, body_head_xy, head_target_h):
    face_path = os.path.join(FACES, side, "f_001.png")
    img = Image.open(face_path).convert("RGBA")
    W, H = img.size

    res = det.detect(mp.Image.create_from_file(face_path))
    if not res.face_landmarks:
        return None
    lm = res.face_landmarks[0]
    tilt = eye_tilt_of(lm, W, H)
    head = np.array([(lm[i].x * W, lm[i].y * H) for i in HEAD_BASE], dtype=np.float64)

    # Baseline ellipse (from user contours), expressed relative to the
    # MediaPipe head center so it follows the head across frames.
    bl = BASE[side]
    bl_cx, bl_cy = bl["center"]          # in 800x800 raw coords
    bl_rx, bl_ry = bl["rx"], bl["ry"]    # rx=wide, ry=tall
    head_cx = head[:, 0].mean()
    head_cy = head[:, 1].mean()
    # offset from head center to baseline center, scaled into the crop frame
    # crop is 400x400 from an 800x800 source => scale 0.5
    scale_crop = W / 800.0
    ox = (bl_cx - 400.0) * scale_crop   # left face baseline center in crop coords
    oy = (bl_cy - 400.0) * scale_crop
    # shift baseline center so it sits on the current head center
    ecx = head_cx + (ox - head_cx) * 1.0
    ecy = head_cy + (oy - head_cy) * 1.0
    # orientation: baseline ellipse is roughly vertical; rotate it by the
    # eye-line tilt so it aligns with the actual head axis in this frame
    orient = tilt  # degrees CCW from vertical

    # 1) source-space mask in padded canvas
    pad = int(max(bl_rx, bl_ry) * 1.6)
    cw, ch = W + 2 * pad, H + 2 * pad
    m = Image.new("L", (cw, ch), 0)
    dd = ImageDraw.Draw(m)
    cx, cy = pad + ecx, pad + ecy
    a, b = bl_rx * scale_crop * 1.0, bl_ry * scale_crop * 1.0
    dd.ellipse([cx - a, cy - b, cx + a, cy + b], fill=255)
    m = m.rotate(orient, center=(cx, cy), resample=Image.BICUBIC)
    m = m.crop((pad, pad, pad + W, pad + H))
    m.save(os.path.join(PREVIEW, f"v19_debug_mask_{side}.png"))
    img.putalpha(m)

    # 2) upright: tilt>0 (right eye lower = face tilted CW) -> rotate CCW +tilt
    img = img.rotate(tilt, center=(W / 2, H / 2), resample=Image.BICUBIC, expand=False)

    rad = math.radians(tilt)
    dx = ecx - W / 2
    dy = ecy - H / 2
    new_cx = dx * math.cos(rad) - dy * math.sin(rad) + W / 2
    new_cy = dx * math.sin(rad) + dy * math.cos(rad) + H / 2

    margin = int(max(bl_rx, bl_ry) * 0.12) * scale_crop
    crop_w = int(2 * (bl_rx * scale_crop + margin))
    crop_h = int(2 * (bl_ry * scale_crop + margin))
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
    erx = int(bl_rx * scale_crop)
    ery = int(bl_ry * scale_crop)
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([crop_w // 2 - erx, crop_h // 2 - ery,
                 crop_w // 2 + erx, crop_h // 2 + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1))
    head_crop.putalpha(em)

    # 4) scale so 2*ery -> head_target_h
    scale = (head_target_h / 2.0) / ery
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    head_crop = head_crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) composite onto user headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(head_crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v19_{tag}_f001.png")
    body.save(out)
    print(f"{tag}: tilt={tilt:+.1f} saved {out}")
    return body

build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 210), 300)
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (150, 62), 105)
print("done")
