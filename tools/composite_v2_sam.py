"""v2 SAM composite (task sam-batch-redo-v2, pilot 2 frames).

Implements D:\dsh\repos\comfyui-worker\tasks\sam-batch-redo-v2\recipe.md
exactly, reusing the approved structure from llama-780m\sam_batch.py:

- Face source: SAM masks from the outbox (mask_<subject>_fNNN.png), NOT
  mediapipe crops. Mediapipe is used only for the eye-center/tilt that the
  approved tight_crop_head needs (same as sam_batch.py).
- Roach:   SAM head mask -> tight_crop_head -> scale head to 0.75x of the
  approved head_target_h=345 (i.e. 259) -> same anchor (RBW//2, RBH*0.19)
  -> resample to 72x148.
- Gorilla: approved gorilla body (blue-ellipse extraction from the source
  jpg) shrunk 0.75x -> SAM head mask -> tight_crop_head -> face scale
  min(2GRX/w, 2GRY/h) * 1.25 -> same anchor (GCX, GCY) -> resample 54x66.
"""
import os, json, math
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

WS = r"D:\dsh workspace\dsh test project"
RAW_DIR = os.path.join(WS, "assets", "raw")
BODIES = os.path.join(WS, "assets", "bodies")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
BASE = json.load(open(os.path.join(WS, "tools", "baseline_ellipses.json")))
OUTBOX = r"C:\Users\gru\.openclaw\workspace\multi-model\shared\work\outbox\sam-batch-redo-v2"
OUT = os.path.join(WS, "llama-780m", "roach-debug", "batch-v2")
GORILLA_BODY = r"C:\Users\gru\Pictures\loj shavale\gorilla-png-37857.jpg"

FRAMES = [("f001", "001"), ("f002", "002")]  # pilot: (frame, subject index)
os.makedirs(OUT, exist_ok=True)

# ---------- bodies (approved loaders from sam_batch.py) ----------
roach_body_tpl = Image.open(os.path.join(BODIES, "cockroach_headless.png")).convert("RGBA")
RBW, RBH = roach_body_tpl.size

def extract_reference_ellipse(path):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(np.float32)
    blue = (a[:,:,2] > 120) & (a[:,:,0] < 100) & (a[:,:,1] < 100)
    ys, xs = np.where(blue)
    if len(xs) == 0: raise RuntimeError("no blue pixels")
    cx = (xs.min() + xs.max()) / 2
    cy = (ys.min() + ys.max()) / 2
    rx = (xs.max() - xs.min()) / 2
    ry = (ys.max() - ys.min()) / 2
    return im, (cx, cy, rx, ry)

def key_white_bg(im):
    a = np.array(im.convert("RGB")).astype(np.float32)
    lum = 0.299*a[:,:,0] + 0.587*a[:,:,1] + 0.114*a[:,:,2]
    sat = a.max(axis=2) - a.min(axis=2)
    white = (lum > 215) & (sat < 40)
    seeds = np.zeros_like(white)
    seeds[0,:] = white[0,:]; seeds[-1,:] = white[-1,:]
    seeds[:,0] = white[:,0]; seeds[:,-1] = white[:,-1]
    seeds = ndimage.binary_dilation(seeds, iterations=3)
    lbl, n = ndimage.label(white)
    bg_labels = set(lbl[seeds].flatten()) - {0}
    bg = np.isin(lbl, list(bg_labels))
    alpha = np.where(bg, 0.0, 1.0)
    alpha_img = Image.fromarray((alpha*255).astype(np.uint8), "L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(2))
    return alpha_img

print("loading gorilla body + ellipse...")
gorilla_body_rgb, (GCX, GCY, GRX, GRY) = extract_reference_ellipse(GORILLA_BODY)
GBW, GBH = gorilla_body_rgb.size
gorilla_alpha = key_white_bg(gorilla_body_rgb)
gorilla_body_tpl = gorilla_body_rgb.convert("RGBA")
gorilla_body_tpl.putalpha(gorilla_alpha)

# v2: shrink the WHOLE gorilla body 0.75x (pre-resize to 54x66), same ellipse
# center — done in full-body space by scaling around (GCX, GCY).
BODY_SHRINK = 0.75
shw, shh = int(GBW * BODY_SHRINK), int(GBH * BODY_SHRINK)
body_small = gorilla_body_tpl.resize((shw, shh), Image.LANCZOS)
sx = shw / GBW
gorilla_body_tpl2 = Image.new("RGBA", (shw, shh), (0, 0, 0, 0))
gorilla_body_tpl2.paste(body_small, (0, 0))
# ellipse center in shrunk space (scale around the image center keeps it
# centered; the recipe says "same ellipse center" — recompute by scaling
# coordinates about the canvas center as the resize did)
cxc = (GBW / 2) * sx
cyc = (GBH / 2) * (shh / GBH)
GCX2 = (GCX - GBW / 2) * sx + cxc
GCY2 = (GCY - GBH / 2) * (shh / GBH) + cyc
GRX2, GRY2 = GRX * sx, GRY * (shh / GBH)
print(f"  gorilla body full {GBW}x{GBH} ellipse=({GCX:.0f},{GCY:.0f}) rx={GRX:.0f} ry={GRY:.0f}")
print(f"  gorilla body shrunk {shw}x{shh} ellipse=({GCX2:.0f},{GCY2:.0f}) rx={GRX2:.0f} ry={GRY2:.0f}")

# mediapipe detector (eye center + tilt, as in sam_batch.py)
base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)
bl = BASE["left"]; br = BASE["right"]

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x*W + lm[133].x*W)/2, (lm[33].y*H + lm[133].y*H)/2)
    e2 = ((lm[362].x*W + lm[263].x*W)/2, (lm[263].x*H + lm[263].y*H)/2)
    tilt = math.degrees(math.atan2(e2[1]-e1[1], e2[0]-e1[0]))
    return (e1[0]+e2[0])/2, (e1[1]+e2[1])/2, tilt

def tight_crop_head(frame, mask_a, cx, cy, rx, ry, split_line, side, W, H):
    """Approved step from sam_batch.py — unchanged."""
    pad = 1.2
    x0 = max(0, int(cx - rx*pad)); y0 = max(0, int(cy - ry*pad))
    x1 = min(W, int(cx + rx*pad)); y1 = min(H, int(cy + ry*pad))
    crop = frame.crop((x0, y0, x1, y1))
    m = mask_a[y0:y1, x0:x1].copy()
    line_x = int(split_line - x0)
    if side == "left": m[:, line_x:] = 0
    else: m[:, :line_x] = 0
    crop.putalpha(Image.fromarray(m, "L"))
    a2 = np.array(crop.getchannel("A"))
    ys, xs = np.where(a2 > 12)
    if len(xs) == 0: return crop
    bx0, bx1 = max(0, xs.min()-3), min(crop.width, xs.max()+3)
    by0, by1 = max(0, ys.min()-3), min(crop.height, ys.max()+3)
    return crop.crop((bx0, by0, bx1, by1))

def tight_crop_alpha(im, thresh=40):
    a = np.array(im.getchannel("A"))
    ys, xs = np.where(a > thresh)
    if len(xs) == 0: return im
    box = (max(0,xs.min()-2), max(0,ys.min()-2), min(im.width,xs.max()+3), min(im.height,ys.max()+3))
    return im.crop(box)

# ---------- v2 builders ----------
ROACH_HEAD_TARGET = int(345 * 0.75)   # 259
GORILLA_FACE_MULT = 1.25
ROACH_OUT = (72, 148)
GORILLA_OUT = (54, 66)

def build_roach_v2(frame, sam_a, rox, roy, roach_tilt):
    head = tight_crop_head(frame, sam_a, rox, roy, bl["rx"], bl["ry"], 400, "left", 800, 800)
    if abs(roach_tilt) > 3:
        head = head.rotate(roach_tilt, center=(head.width/2, head.height/2),
                           resample=Image.BICUBIC, expand=False)
    body = roach_body_tpl.copy()
    scale = ROACH_HEAD_TARGET / head.height
    new_w, new_h = int(head.width * scale), int(head.height * scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    hx, hy = RBW // 2, int(RBH * 0.19)   # anchor UNCHANGED
    body.alpha_composite(head, (hx - new_w // 2, hy - new_h // 2))
    return body.resize(ROACH_OUT, Image.LANCZOS)

def build_gorilla_v2(frame, sam_a, gox, goy, gorilla_tilt):
    head = tight_crop_head(frame, sam_a, gox, goy, br["rx"], br["ry"], 400, "right", 800, 800)
    if abs(gorilla_tilt) > 3:
        head = head.rotate(gorilla_tilt, center=(head.width/2, head.height/2),
                           resample=Image.BICUBIC, expand=False)
    body = gorilla_body_tpl2.copy()   # already shrunk 0.75x
    scale = min((2*GRX2) / head.width, (2*GRY2) / head.height) * GORILLA_FACE_MULT
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    # clip head alpha to the (shrunk) ellipse
    head_a = np.array(head.getchannel("A"), dtype=np.float32)
    ell = Image.new("L", (new_w, new_h), 0)
    de = ImageDraw.Draw(ell)
    de.ellipse([new_w/2 - GRX2, new_h/2 - GRY2, new_w/2 + GRX2, new_h/2 + GRY2], fill=255)
    ell = ell.filter(ImageFilter.GaussianBlur(8))
    head_a *= np.array(ell, dtype=np.float32) / 255.0
    head.putalpha(Image.fromarray(head_a.astype(np.uint8), "L"))
    body.alpha_composite(head, (int(GCX2 - new_w/2), int(GCY2 - new_h/2)))
    body = tight_crop_alpha(body, thresh=40)
    return body.resize(GORILLA_OUT, Image.LANCZOS)

# ---------- main ----------
for tag, idx in FRAMES:
    raw_path = os.path.join(RAW_DIR, f"raw_{tag}.png")
    # outbox masks are per-subject combined masks; the roach/gorilla masks are
    # identical combined per-frame masks (manifest note). Use the roach mask
    # for both (it is the combined mask of the frame).
    mask_path = os.path.join(OUTBOX, f"mask_roach_{idx}_{tag}.png")
    sam_mask = Image.open(mask_path).convert("L")
    sam_mask = sam_mask.filter(ImageFilter.MinFilter(5))
    sam_mask = sam_mask.filter(ImageFilter.GaussianBlur(0.8))
    sam_a = np.array(sam_mask)
    raw = Image.open(raw_path).convert("RGBA")
    W, H = raw.size
    frame = raw.copy()
    frame.putalpha(sam_mask)
    res = det.detect(mp.Image.create_from_file(raw_path))
    faces = list(res.face_landmarks)
    left_lm = next((f for f in faces if f[1].x * W < W/2), None)
    right_lm = next((f for f in faces if f[1].x * W >= W/2), None)
    if left_lm is None or right_lm is None:
        print(f"{tag}: mediapipe found {len(faces)} faces — SKIP")
        continue
    rox, roy, roach_tilt = eye_mid_and_tilt(left_lm, W, H)
    gox, goy, gorilla_tilt = eye_mid_and_tilt(right_lm, W, H)
    roach = build_roach_v2(frame, sam_a, rox, roy, roach_tilt)
    gorilla = build_gorilla_v2(frame, sam_a, gox, goy, gorilla_tilt)
    roach.save(os.path.join(OUT, f"roach_{tag}.png"))
    gorilla.save(os.path.join(OUT, f"gorilla_{tag}.png"))
    print(f"{tag}: roach {roach.size} gorilla {gorilla.size}  "
          f"(roach eye=({rox:.0f},{roy:.0f}) tilt={roach_tilt:.1f}  "
          f"gorilla eye=({gox:.0f},{goy:.0f}) tilt={gorilla_tilt:.1f})")
print("done")
