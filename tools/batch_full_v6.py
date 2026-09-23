"""Full 53-frame batch, v6 recipe (roach head 259px / gorilla face 1.25x body
0.75x). Reuses the exact v5/v6 functions. Outputs masters + smalls to
assets/final_small/{roach,gorilla}/f_NNN.png (smalls) and batch-v6-full masters.
Frames f001..f053 -> masks samtest_batch_001..053.
"""
import os, sys, math, time
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

WS = r"D:\dsh workspace\dsh test project"
RAW_DIR = os.path.join(WS, "assets", "raw")
BODIES = os.path.join(WS, "assets", "bodies")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
COM = r"D:\ComfyUI-Container\workspace\output"
FINAL = os.path.join(WS, "assets", "final_small")
OUT = os.path.join(WS, "llama-780m", "roach-debug", "batch-v6-full")
GORILLA_BODY = r"C:\Users\gru\Pictures\loj shavale\gorilla-png-37857.jpg"

os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(FINAL, "roach"), exist_ok=True)
os.makedirs(os.path.join(FINAL, "gorilla"), exist_ok=True)

# ---- v6 recipe functions (copied from composite_v5_sam.py) ----
def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x*W + lm[133].x*W)/2, (lm[33].y*H + lm[133].y*H)/2)
    e2 = ((lm[362].x*W + lm[263].x*W)/2, (lm[263].y*H + lm[263].y*H)/2)
    tilt = math.degrees(math.atan2(e2[1]-e1[1], e2[0]-e1[0]))
    return (e1[0]+e2[0])/2, (e1[1]+e2[1])/2, tilt

def _notch_right_edge(mask_a, y_lo, y_hi, search_x1):
    edges = []
    for y in range(max(0, y_lo), min(mask_a.shape[0], y_hi)):
        xs = np.where(mask_a[y] > 12)[0]
        if len(xs) == 0:
            continue
        run_end = xs[0]
        for x in xs[1:]:
            if x - run_end > 1:
                break
            run_end = x
        if run_end - xs[0] > 30 and run_end < search_x1:
            edges.append(run_end)
    if not edges:
        return None
    return int(np.median(edges))

def tight_crop_head(frame, mask_a, cx, cy, rx, ry, side):
    pad = 1.2
    x0 = max(0, int(cx - rx*pad)); y0 = max(0, int(cy - ry*pad))
    x1 = min(frame.width, int(cx + rx*pad)); y1 = min(frame.height, int(cy + ry*pad))
    crop = frame.crop((x0, y0, x1, y1))
    m = mask_a[y0:y1, x0:x1].copy()
    if side == "left":
        notch = _notch_right_edge(mask_a, 230, 300, 470)
        if notch is not None:
            m[:, notch - x0:] = 0
        else:
            m[:, 400 - x0:] = 0
    else:
        m[:, :400 - x0] = 0
    crop.putalpha(Image.fromarray(m, "L"))
    a2 = np.array(crop.getchannel("A"))
    ys, xs = np.where(a2 > 12)
    if len(xs) == 0: return crop
    bx0, bx1 = max(0, xs.min()-3), min(crop.width, xs.max()+3)
    by0, by1 = max(0, ys.min()-3), min(crop.height, ys.max()+3)
    return crop.crop((bx0, by0, bx1, by1))

def tight_crop_alpha(im, thresh=8):
    a = np.array(im.getchannel("A"))
    ys, xs = np.where(a > thresh)
    if len(xs) == 0: return im
    box = (max(0,xs.min()-2), max(0,ys.min()-2), min(im.width,xs.max()+3), min(im.height,ys.max()+3))
    return im.crop(box)

def extract_reference_ellipse(path):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(np.float32)
    blue = (a[:,:,2] > 120) & (a[:,:,0] < 100) & (a[:,:,1] < 100)
    ys, xs = np.where(blue)
    if len(xs) == 0: raise RuntimeError("no blue pixels")
    return im, ((xs.min()+xs.max())/2, (ys.min()+ys.max())/2,
                (xs.max()-xs.min())/2, (ys.max()-ys.min())/2)

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
    return Image.fromarray((alpha*255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2))

def build_roach(frame, sam_a, rox, roy, roach_tilt, head_target=259,
                RBW=358, RBH=734):
    head = tight_crop_head(frame, sam_a, rox, roy, 233.73, 294.26, "left")
    if abs(roach_tilt) > 3:
        head = head.rotate(roach_tilt, center=(head.width/2, head.height/2),
                           resample=Image.BICUBIC, expand=False)
    body = ROACH_BODY.copy()
    scale = head_target / head.height
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    hx, hy = RBW//2, int(RBH*0.19)
    body.alpha_composite(head, (hx - new_w//2, hy - new_h//2))
    return body

def build_gorilla(frame, sam_a, gox, goy, face_scale=1.25, body_scale=0.75):
    head = tight_crop_head(frame, sam_a, gox, goy, 239.65, 283.11, "right")
    body = GORILLA_BODY_TPL.copy()
    if body_scale != 1.0:
        body = body.resize((int(GBW*body_scale), int(GBH*body_scale)), Image.LANCZOS)
    BW2, BH2 = body.size
    bx = BW2/GBW; by = BH2/GBH
    cx2, cy2 = GCX*bx, GCY*by
    rx2, ry2 = GRX*bx*face_scale, GRY*by*face_scale
    m = Image.new("L", (BW2, BH2), 255)
    d = ImageDraw.Draw(m)
    d.ellipse([cx2-rx2, cy2-ry2, cx2+rx2, cy2+ry2], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(25))
    a = np.array(body.getchannel("A"), dtype=np.float32)
    body.putalpha(Image.fromarray((a*np.array(m, dtype=np.float32)/255.0).astype(np.uint8), "L"))
    scale = min((2*rx2)/head.width, (2*ry2)/head.height)
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    head_a = np.array(head.getchannel("A"), dtype=np.float32)
    ell = Image.new("L", (new_w, new_h), 0)
    de = ImageDraw.Draw(ell)
    de.ellipse([new_w/2-rx2, new_h/2-ry2, new_w/2+rx2, new_h/2+ry2], fill=255)
    ell = ell.filter(ImageFilter.GaussianBlur(8))
    head_a *= np.array(ell, dtype=np.float32)/255.0
    head.putalpha(Image.fromarray(head_a.astype(np.uint8), "L"))
    body.alpha_composite(head, (int(cx2-new_w/2), int(cy2-new_h/2)))
    return tight_crop_alpha(body, thresh=40)

# ---- load bodies ----
print("loading bodies...")
gorilla_body_rgb, (GCX, GCY, GRX, GRY) = extract_reference_ellipse(GORILLA_BODY)
GBW, GBH = gorilla_body_rgb.size
GORILLA_BODY_TPL = gorilla_body_rgb.convert("RGBA")
GORILLA_BODY_TPL.putalpha(key_white_bg(gorilla_body_rgb))
ROACH_BODY = Image.open(os.path.join(BODIES, "cockroach_headless.png")).convert("RGBA")
RBW, RBH = ROACH_BODY.size
print(f"  gorilla {GBW}x{GBH} ellipse=({GCX:.0f},{GCY:.0f}) rx={GRX:.0f} ry={GRY:.0f}")
print(f"  roach   {RBW}x{RBH}")

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

# ---- run ----
t0 = time.time()
results = []
for n in range(1, 54):
    tag = f"f{n:03d}"
    raw_path = os.path.join(RAW_DIR, f"raw_{tag}.png")
    mask_path = os.path.join(COM, f"samtest_batch_{n:03d}_00001_.png")
    if not os.path.exists(raw_path) or not os.path.exists(mask_path):
        print(f"{tag}: MISSING raw or mask — SKIP")
        results.append((tag, "skip", "missing"))
        continue
    try:
        sam = Image.open(mask_path).convert("L")
        sam = sam.filter(ImageFilter.MinFilter(5))
        sam = sam.filter(ImageFilter.GaussianBlur(0.8))
        sam_a = np.array(sam)
        raw = Image.open(raw_path).convert("RGBA")
        W, H = raw.size
        frame = raw.copy()
        frame.putalpha(sam)
        res = det.detect(mp.Image.create_from_file(raw_path))
        faces = list(res.face_landmarks)
        left_lm = next((f for f in faces if f[1].x * W < W/2), None)
        right_lm = next((f for f in faces if f[1].x * W >= W/2), None)
        if left_lm is None or right_lm is None:
            print(f"{tag}: mediapipe {len(faces)} faces — SKIP")
            results.append((tag, "skip", "faces"))
            continue
        rox, roy, roach_tilt = eye_mid_and_tilt(left_lm, W, H)
        gox, goy, _ = eye_mid_and_tilt(right_lm, W, H)
        roach_master = build_roach(frame, sam_a, rox, roy, roach_tilt, head_target=259, RBW=RBW, RBH=RBH)
        gorilla_master = build_gorilla(frame, sam_a, gox, goy, face_scale=1.25, body_scale=0.75)
        roach_small = roach_master.resize((72, 148), Image.LANCZOS)
        gorilla_small = gorilla_master.resize((54, 66), Image.LANCZOS)
        roach_small.save(os.path.join(FINAL, "roach", f"f_{n:03d}.png"))
        gorilla_small.save(os.path.join(FINAL, "gorilla", f"f_{n:03d}.png"))
        roach_master.save(os.path.join(OUT, f"roach_{tag}_master.png"))
        gorilla_master.save(os.path.join(OUT, f"gorilla_{tag}_master.png"))
        print(f"{tag}: OK roach {roach_master.size} gorilla {gorilla_master.size} (tilt {roach_tilt:.1f})")
        results.append((tag, "ok", ""))
    except Exception as e:
        print(f"{tag}: ERROR {e}")
        results.append((tag, "error", str(e)))

ok = sum(1 for _, s, _ in results if s == "ok")
skip = sum(1 for _, s, _ in results if s == "skip")
err = sum(1 for _, s, _ in results if s == "error")
print(f"\nDONE in {time.time()-t0:.0f}s: {ok} ok, {skip} skip, {err} error")
if skip or err:
    print("skips/errors:", [(t, s, r) for t, s, r in results if s != "ok"])
