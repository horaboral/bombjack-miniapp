"""v27: contour-matched compositing.

Per the user: the target ellipse I place on each headless body must have
the SAME contour as the face contour the user drew. The face content
scales so the drawn contour maps exactly onto the target ellipse.

Steps:
1. Detect the face, compute eye-line tilt.
2. Crop a generous region around the contour center from the raw frame.
3. Rotate the crop so the face is upright (only if |tilt| > 10).
4. In the rotated crop, place the user's baseline ellipse (same shape,
   rotated by -tilt) as the alpha mask.
5. Scale the masked crop so 2*ery -> head_target_h.
6. Composite onto the headless body at the body anchor.

The mask IS the user's contour shape; the content inside it is the real
face at the matching scale. No black ellipse, no halo: the mask is the
face boundary.
"""
import os, math, json
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
RAW = os.path.join(WS, "assets", "raw", "raw_f001.png")
BODIES = os.path.join(WS, "assets", "bodies")
PREVIEW = os.path.join(WS, "assets", "preview")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x * W + lm[133].x * W) / 2, (lm[33].y * H + lm[133].y * H) / 2)
    e2 = ((lm[362].x * W + lm[263].x * W) / 2, (lm[362].y * H + lm[263].y * H) / 2)
    tilt = math.degrees(math.atan2(e2[1] - e1[1], e2[0] - e1[0]))
    return (e1[0] + e2[0]) / 2, (e1[1] + e2[1]) / 2, tilt

def build(tag, side, body_path, body_head_xy, head_target_h):
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

    bl = BASE[side]
    erx, ery = bl["rx"], bl["ry"]
    if side == "left":
        off_x, off_y = 254 - emx, 411 - emy
    else:
        off_x, off_y = 691 - emx, 443 - emy
    cx, cy = emx + off_x, emy + off_y
    print(f"{tag}: eye_mid=({emx:.0f},{emy:.0f}) tilt={tilt:+.1f} "
          f"contour=({cx:.0f},{cy:.0f}) er=({erx:.0f},{ery:.0f})")

    # 1) crop a generous region around the contour center (in raw coords)
    margin = int(max(erx, ery) * 0.12)
    crop_w = int(2 * (erx + margin))
    crop_h = int(2 * (ery + margin))
    x0 = int(cx - crop_w / 2)
    y0 = int(cy - crop_h / 2)
    pxx = max(0, -x0); pyy = max(0, -y0)
    nxx = max(0, x0 + crop_w - W); nyy = max(0, y0 + crop_h - H)
    if pxx or pyy or nxx or nyy:
        big = Image.new("RGBA", (W + pxx + nxx, H + pyy + nyy), (0, 0, 0, 0))
        big.paste(raw, (pxx, pyy))
        x0 += pxx; y0 += pyy
        raw = big
    crop = raw.crop((x0, y0, x0 + crop_w, y0 + crop_h))
    # crop center (in crop coords)
    ccx, ccy = crop_w / 2, crop_h / 2

    # 2) upright the face: rotate crop by +tilt around its center
    #    (PIL rotates CCW; a face tilted +tilt (eye line rising to the
    #     right) needs a -tilt CCW rotation to become horizontal, i.e.
    #     rotate(-tilt). We match the v22 convention that worked: the
    #     mask was rotated by -tilt and the image by +tilt, netting an
    #     upright face with an axis-aligned ellipse.)
    if abs(tilt) > 10:
        crop = crop.rotate(tilt, center=(ccx, ccy), resample=Image.BICUBIC,
                           expand=False)

    # 3) alpha mask: the user's contour ellipse, axis-aligned in the
    #    (now upright) crop, centered on the crop center.
    em = Image.new("L", (crop_w, crop_h), 0)
    edd = ImageDraw.Draw(em)
    edd.ellipse([ccx - erx, ccy - ery, ccx + erx, ccy + ery], fill=255)
    em = em.filter(ImageFilter.GaussianBlur(1.2))
    crop.putalpha(em)

    # 4) scale so 2*ery -> head_target_h (the contour maps 1:1 onto the
    #    target ellipse on the body)
    scale = (head_target_h / 2.0) / ery
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)
    crop = crop.resize((new_w, new_h), Image.LANCZOS)

    # 5) composite onto the headless body
    body = Image.open(body_path).convert("RGBA")
    bx, by = body_head_xy
    body.alpha_composite(crop, (bx - new_w // 2, by - new_h // 2))
    out = os.path.join(PREVIEW, f"v27_{tag}_f001.png")
    body.save(out)
    print(f"  new=({new_w},{new_h}) saved {out}")
    return body

# Roach: head sits in the white area between the antennae bases and the
# brown collar; anchor near the top of the white patch.
build("roach", "left", os.path.join(BODIES, "roach_headless.jpg"), (400, 150), 230)
# Gorilla: the tan patch center.
build("gorilla", "right", os.path.join(BODIES, "gorilla_headless.jpg"), (121, 107), 110)
print("done")
