"""v3 SAM composite — master-first, quality bar = v11b gorilla / rebuild roach improved.

Working order (per igol): build the big high-quality master first; the small
display size is ONLY a downsample of that master — never a separate composite.

- Gorilla: v11b pipeline unchanged — full-res 2204x2926 body, SAM cut, face
  fills the blue ellipse at 1.0x, no tilt. Master = tight-cropped full-res
  composite; small = LANCZOS downsample to 54x66.
- Roach: SAM cut + baseline left-ellipse refinement (major_angle 9.86°),
  the same two-layer cut as v11b (option 1 per igol). Head target 0.75x of
  the approved 345 (=259), same anchor (RBW//2, RBH*0.19). Master = 358x734
  composite; small = LANCZOS downsample to 72x148.
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
OUT = os.path.join(WS, "llama-780m", "roach-debug", "batch-v3")
GORILLA_BODY = r"C:\Users\gru\Pictures\loj shavale\gorilla-png-37857.jpg"

FRAMES = [("f001", "001"), ("f002", "002")]
os.makedirs(OUT, exist_ok=True)

bl = BASE["left"]; br = BASE["right"]

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x*W + lm[133].x*W)/2, (lm[33].y*H + lm[133].y*H)/2)
    e2 = ((lm[362].x*W + lm[263].x*W)/2, (lm[263].y*H + lm[263].y*H)/2)
    tilt = math.degrees(math.atan2(e2[1]-e1[1], e2[0]-e1[0]))
    return (e1[0]+e2[0])/2, (e1[1]+e2[1])/2, tilt

def _notch_right_edge(mask_a, y_lo, y_hi, search_x1):
    """Right edge of the LEFT face in the row band where the two faces
    separate (per-row probe: stable at x~424-427). None if no band found."""
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

def tight_crop_head(frame, mask_a, cx, cy, rx, ry, split_line, side, W, H):
    """SAM-mask cut, tight bbox.

    The combined mask only separates the faces in a narrow band (y~241-291,
    gap x~427-460); below it the blob is continuous. For the left face we
    clamp the mask's right edge to the notch (left face's right edge in the
    separation band) so the gorilla's shoulder/neck never enters the roach
    cut. Right face uses the mask directly.
    """
    pad = 1.2
    x0 = max(0, int(cx - rx*pad)); y0 = max(0, int(cy - ry*pad))
    x1 = min(W, int(cx + rx*pad)); y1 = min(H, int(cy + ry*pad))
    crop = frame.crop((x0, y0, x1, y1))
    m = mask_a[y0:y1, x0:x1].copy()
    if side == "left":
        notch = _notch_right_edge(mask_a, 230, 300, 470)
        if notch is not None:
            m[:, notch - x0:] = 0
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

# ---------- bodies (v11b loaders, unchanged) ----------
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
    alpha_img = Image.fromarray((alpha*255).astype(np.uint8), "L")
    return alpha_img.filter(ImageFilter.GaussianBlur(2))

print("loading bodies...")
gorilla_body_rgb, (GCX, GCY, GRX, GRY) = extract_reference_ellipse(GORILLA_BODY)
GBW, GBH = gorilla_body_rgb.size
gorilla_body_tpl = gorilla_body_rgb.convert("RGBA")
gorilla_body_tpl.putalpha(key_white_bg(gorilla_body_rgb))
print(f"  gorilla body {GBW}x{GBH} ellipse=({GCX:.0f},{GCY:.0f}) rx={GRX:.0f} ry={GRY:.0f}")

roach_body_tpl = Image.open(os.path.join(BODIES, "cockroach_headless.png")).convert("RGBA")
RBW, RBH = roach_body_tpl.size

base = mp.tasks.BaseOptions(model_asset_path=MODEL)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=base, num_faces=2,
                                             min_face_detection_confidence=0.3)
det = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

# ---------- builders ----------
ROACH_HEAD_TARGET = int(345 * 0.75)   # 259 (v2 recipe)
ROACH_SMALL = (72, 148)
GORILLA_SMALL = (54, 66)

def build_roach_v3(frame, sam_a, rox, roy, roach_tilt):
    """SAM cut + baseline left-ellipse (9.86° tilt) — option 1."""
    head = tight_crop_head(frame, sam_a, rox, roy, bl["rx"], bl["ry"], 400, "left", 800, 800)
    if abs(roach_tilt) > 3:
        head = head.rotate(roach_tilt, center=(head.width/2, head.height/2),
                           resample=Image.BICUBIC, expand=False)
    # two-layer cut: keep SAM cut, then multiply by the baseline ellipse
    # (major_angle tilt) as the refinement mask — same architecture as v11b.
    ew, eh = head.width, head.height
    ell = Image.new("L", (ew, eh), 0)
    de = ImageDraw.Draw(ell)
    # ellipse radii: fit the head frame; the baseline ellipse is the face
    # proportion reference (rx 233.7, ry 294.3) — scale to the head frame.
    erx = ew / 2 * 0.98
    ery = eh / 2 * 0.98
    de.ellipse([ew/2-erx, eh/2-ery, ew/2+erx, eh/2+ery], fill=255)
    ell = ell.rotate(bl.get("major_angle", 9.86), center=(ew/2, eh/2),
                     resample=Image.BICUBIC)
    ell = ell.filter(ImageFilter.GaussianBlur(3))
    ha = np.array(head.getchannel("A"), dtype=np.float32)
    ha *= np.array(ell, dtype=np.float32) / 255.0
    head.putalpha(Image.fromarray(ha.astype(np.uint8), "L"))
    # master: full-res composite at the approved anchor
    body = roach_body_tpl.copy()
    scale = ROACH_HEAD_TARGET / head.height
    new_w, new_h = int(head.width * scale), int(head.height * scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    hx, hy = RBW // 2, int(RBH * 0.19)
    body.alpha_composite(head, (hx - new_w // 2, hy - new_h // 2))
    # small: downsample of the MASTER (never a separate composite)
    small = body.resize(ROACH_SMALL, Image.LANCZOS)
    return body, small

def build_gorilla_v3(frame, sam_a, gox, goy):
    """v11b pipeline unchanged."""
    head = tight_crop_head(frame, sam_a, gox, goy, br["rx"], br["ry"], 400, "right", 800, 800)
    body = gorilla_body_tpl.copy()
    m = Image.new("L", (GBW, GBH), 255)
    d = ImageDraw.Draw(m)
    d.ellipse([GCX-GRX, GCY-GRY, GCX+GRX, GCY+GRY], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(25))
    a = np.array(body.getchannel("A"), dtype=np.float32)
    mm = np.array(m, dtype=np.float32)/255.0
    body.putalpha(Image.fromarray((a*mm).astype(np.uint8), "L"))
    scale = min((2*GRX)/head.width, (2*GRY)/head.height)
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    head_a = np.array(head.getchannel("A"), dtype=np.float32)
    ell = Image.new("L", (new_w, new_h), 0)
    de = ImageDraw.Draw(ell)
    de.ellipse([new_w/2-GRX, new_h/2-GRY, new_w/2+GRX, new_h/2+GRY], fill=255)
    ell = ell.filter(ImageFilter.GaussianBlur(8))
    head_a *= np.array(ell, dtype=np.float32)/255.0
    head.putalpha(Image.fromarray(head_a.astype(np.uint8), "L"))
    body.alpha_composite(head, (int(GCX-new_w/2), int(GCY-new_h/2)))
    # master = tight-cropped full-res composite (v11b small pipeline)
    master = tight_crop_alpha(body, thresh=40)
    small = master.resize(GORILLA_SMALL, Image.LANCZOS)
    return master, small

# ---------- main ----------
for tag, idx in FRAMES:
    raw_path = os.path.join(RAW_DIR, f"raw_{tag}.png")
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
    gox, goy, _ = eye_mid_and_tilt(right_lm, W, H)
    roach_master, roach_small = build_roach_v3(frame, sam_a, rox, roy, roach_tilt)
    gora_master, gora_small = build_gorilla_v3(frame, sam_a, gox, goy)
    roach_master.save(os.path.join(OUT, f"roach_{tag}_master.png"))
    roach_small.save(os.path.join(OUT, f"roach_{tag}.png"))
    gora_master.save(os.path.join(OUT, f"gorilla_{tag}_master.png"))
    gora_small.save(os.path.join(OUT, f"gorilla_{tag}.png"))
    print(f"{tag}: roach master {roach_master.size} -> small {roach_small.size} (tilt {roach_tilt:.1f})  "
          f"gorilla master {gora_master.size} -> small {gora_small.size} (no tilt)")
print("done")
