"""v26: Use the user-drawn contours (filled) as the head shape on each
headless body. The face content from the raw video frame is masked by
the contour and composited onto the body. No visible ellipse border."""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
RAW = os.path.join(WS, "assets", "raw", "raw_f001.png")
BODIES = os.path.join(WS, "assets", "bodies")
CONTOURS = os.path.join(WS, "assets", "contours")
PREVIEW = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    tilt = math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))
    return (e1[0] + e2[0]) / 2, (e1[1] + e2[1]) / 2, tilt

def build(tag, side, body_path, body_head_center, head_h):
    """body_head_center: (cx, cy) where the top of the head contour should
    be placed on the body. head_h: target height of the head contour in
    body pixels."""
    body = Image.open(body_path).convert("RGBA")
    BW, BH = body.size

    # 1) Load the filled contour mask for this side
    contour = Image.open(os.path.join(CONTOURS, f"filled_{side}.png"))
    cw, ch = contour.size

    # 2) Get the face landmarks from the raw frame
    raw = Image.open(RAW).convert("RGBA")
    W, H = raw.size  # 800x800
    res = det.detect(mp.Image.create_from_file(RAW))
    if not res.face_landmarks:
        return None
    lm = None
    for f in res.face_landmarks:
        fx = f[1].x * W
        if (side == "left" and fx < W / 2) or (side == "right" and fx >= W / 2):
            lm = f; break
    if lm is None:
        return None
    emx, emy, tilt = eye_mid_and_tilt(lm, W, H)

    # 3) Scale the contour mask to the target head height
    scale = head_h / ch
    new_cw = int(cw * scale)
    new_ch = int(ch * scale)
    contour_resized = contour.resize((new_cw, new_ch), Image.LANCZOS)

    # 4) Take the face content from the raw frame, centered on the eye midpoint.
    #    The face region should be large enough to cover the contour.
    face_margin = int(max(new_cw, new_ch) * 0.15)
    face_w = new_cw + 2 * face_margin
    face_h = new_ch + 2 * face_margin
    # Face center in raw coords: use the contour center mapped from the
    # contour's own center. The contour's center in the marked image is
    # approximately the eye midpoint area.
    # Actually, let's just take a crop from the raw frame centered on the
    # eye midpoint, sized to cover the contour.
    fx0 = int(emx - face_w / 2)
    fy0 = int(emy - face_h / 2)
    # Pad if out of bounds
    pxx = max(0, -fx0); pyy = max(0, -fy0)
    nxx = max(0, fx0 + face_w - W); nyy = max(0, fy0 + face_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(raw, (pxx, pyy))
        fx0 += pxx; fy0 += pyy
        raw = big
    face_crop = raw.crop((fx0, fy0, fx0 + face_w, fy0 + face_h))

    # 5) Upright the face if tilted (rotate the crop)
    if abs(tilt) > 10:
        face_crop = face_crop.rotate(tilt, center=(face_w / 2, face_h / 2),
                                      resample=Image.BICUBIC, expand=False)

    # 6) Apply the contour mask to the face crop.
    #    The contour mask is new_cw x new_ch. The face crop is face_w x face_h.
    #    Center the contour mask on the face crop.
    mask_on_face = Image.new("L", (face_w, face_h), 0)
    mx = (face_w - new_cw) // 2
    my = (face_h - new_ch) // 2
    mask_on_face.paste(contour_resized, (mx, my))
    # Smooth the mask edges
    mask_on_face = mask_on_face.filter(ImageFilter.GaussianBlur(1))
    face_crop.putalpha(mask_on_face)

    # 7) Composite onto the body, centered on body_head_center
    bx, by = body_head_center
    paste_x = bx - face_w // 2
    paste_y = by - face_h // 2
    body.alpha_composite(face_crop, (paste_x, paste_y))

    out = os.path.join(PREVIEW, f"v26_{tag}_f001.png")
    body.save(out)
    print(f"{tag}: tilt={tilt:+.1f} contour=({new_cw}x{new_ch}) face=({face_w}x{face_h}) "
          f"paste=({paste_x},{paste_y}) saved")
    return body

# Roach: body is 800x800, head area is around (400, 150), head height ~300
build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 150), 300)
# Gorilla: body is 300x232, head area is around (121, 107), head height ~105
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (121, 107), 105)
print("done")
