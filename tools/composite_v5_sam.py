"""v5 = v11b pipeline EXACTLY (mediapipe per-frame centers, pad 1.2, tight
bbox, fixed split), with ONE fix: the roach's right edge follows the per-row
separation notch instead of the fixed x=400 line (which cut a dark wedge).

Everything else is byte-for-byte the approved v11b recipe:
  roach   : rotate tilt, head height -> 345, anchor (BW//2, BH*0.19)
  gorilla : erase body ellipse, head fits min(2rx/w, 2ry/h), ellipse clip blur 8

Master first; small is only a LANCZOS downsample of the master.
Per-frame masks: D:\\ComfyUI-Container\\workspace\\output\\samtest_batch_NNN_00001_.png
"""
import os, math
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

WS = r"D:\dsh workspace\dsh test project"
RAW_DIR = os.path.join(WS, "assets", "raw")
BODIES = os.path.join(WS, "assets", "bodies")
MODEL = os.path.join(WS, "tools", "face_landmarker.task")
COM = r"D:\ComfyUI-Container\workspace\output"
OUT = os.path.join(WS, "llama-780m", "roach-debug", "batch-v6")
GORILLA_BODY = r"C:\Users\gru\Pictures\loj shavale\gorilla-png-37857.jpg"

FRAMES = [("f001", "001"), ("f002", "002")]
os.makedirs(OUT, exist_ok=True)

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x*W + lm[133].x*W)/2, (lm[33].y*H + lm[133].y*H)/2)
    e2 = ((lm[362].x*W + lm[263].x*W)/2, (lm[263].y*H + lm[263].y*H)/2)
    tilt = math.degrees(math.atan2(e2[1]-e1[1], e2[0]-e1[0]))
    return (e1[0]+e2[0])/2, (e1[1]+e2[1])/2, tilt

def _notch_right_edge(mask_a, y_lo, y_hi, search_x1):
    """Right edge of the LEFT face in the row band where the two faces
    separate (probe: stable ~x424-427). None if no band."""
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
    """v11b tight_crop_head, but the left side uses the per-row notch as its
    right boundary instead of a fixed x=400 line."""
    pad = 1.2
    x0 = max(0, int(cx - rx*pad)); y0 = max(0, int(cy - ry*pad))
    x1 = min(frame.width, int(cx + rx*pad)); y1 = min(frame.height, int(cy + ry*pad))
    crop = frame.crop((x0, y0, x1, y1))
    m = mask_a[y0:y1, x0:x1].copy()
    if side == "left":
        # right boundary = the notch (left face's right edge in the band where
        # faces separate). For rows below the band, clamp to the notch too so
        # the gorilla's merged neck never enters the roach cut.
        notch = _notch_right_edge(mask_a, 230, 300, 470)
        if notch is not None:
            m[:, notch - x0:] = 0
        else:
            m[:, 400 - x0:] = 0  # fall back to v11b fixed line
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

def build_roach(frame, sam_a, rox, roy, roach_tilt, head_target=345):
    """v11b roach: mediapipe center window, notch split, tilt, h->head_target.
    head_target=345 is full approved; 259 is the 25% rescale (0.75x)."""
    head = tight_crop_head(frame, sam_a, rox, roy, 233.73, 294.26, "left")
    if abs(roach_tilt) > 3:
        head = head.rotate(roach_tilt, center=(head.width/2, head.height/2),
                           resample=Image.BICUBIC, expand=False)
    body = roach_body_tpl.copy()
    scale = head_target / head.height
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    hx, hy = RBW//2, int(RBH*0.19)
    body.alpha_composite(head, (hx - new_w//2, hy - new_h//2))
    master = body
    small = body.resize((72, 148), Image.LANCZOS)   # display size of the 25% rescale
    return master, small

def build_gorilla(frame, sam_a, gox, goy, face_scale=1.0, body_scale=1.0):
    """v11b gorilla: mediapipe center window, fixed split, fit ellipse,
    ellipse clip blur 8, NO tilt. face_scale/body_scale apply the 25% rescale
    (face 1.25x / body 0.75x); defaults 1.0/1.0 = full approved v11b."""
    head = tight_crop_head(frame, sam_a, gox, goy, 239.65, 283.11, "right")
    body = gorilla_body_tpl.copy()
    if body_scale != 1.0:
        body = body.resize((int(GBW*body_scale), int(GBH*body_scale)), Image.LANCZOS)
    BW2, BH2 = body.size
    bx = BW2/GBW; by = BH2/GBH
    cx2, cy2 = GCX*bx, GCY*by
    rx2, ry2 = GRX*bx*face_scale, GRY*by*face_scale   # face fills scaled ellipse x face_scale
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
    master = tight_crop_alpha(body, thresh=40)
    small = master.resize((54, 66), Image.LANCZOS)
    return master, small

for tag, idx in FRAMES:
    raw_path = os.path.join(RAW_DIR, f"raw_{tag}.png")
    mask_path = os.path.join(COM, f"samtest_batch_{idx}_00001_.png")
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
        print(f"{tag}: mediapipe found {len(faces)} faces — SKIP"); continue
    rox, roy, roach_tilt = eye_mid_and_tilt(left_lm, W, H)
    gox, goy, _ = eye_mid_and_tilt(right_lm, W, H)
    # 25% rescale: roach head 0.75x (345->259); gorilla face 1.25x / body 0.75x
    rm, rs = build_roach(frame, sam_a, rox, roy, roach_tilt, head_target=259)
    gm, gs = build_gorilla(frame, sam_a, gox, goy, face_scale=1.25, body_scale=0.75)
    rm.save(os.path.join(OUT, f"roach_{tag}_master.png"))
    rs.save(os.path.join(OUT, f"roach_{tag}.png"))
    gm.save(os.path.join(OUT, f"gorilla_{tag}_master.png"))
    gs.save(os.path.join(OUT, f"gorilla_{tag}.png"))
    print(f"{tag}: roach {rm.size}->{rs.size} (tilt {roach_tilt:.1f})  gorilla {gm.size}->{gs.size}")
print("done")
