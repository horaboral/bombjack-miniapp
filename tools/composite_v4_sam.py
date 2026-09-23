"""v4 SAM composite — ELLIPSE-ANCHORED (the architecture igol confirmed).

The stable frame is the baseline (mediapipe) ellipse in raw-frame coords;
the SAM mask is only the clean alpha cut INSIDE that ellipse. This removes
the per-frame mask-bbox drift that made v3's gorilla face too small and
the roach halo.

- Gorilla: face fills the body's blue ellipse (fixed rx/ry), SAM mask cut
  inside it, no tilt. Master = full-res 2204x2926 composite; small = LANCZOS
  downsample to 54x66.
- Roach: face placed at the baseline left ellipse (rx 233.7, ry 294.3,
  major_angle 9.86 deg) in raw-frame coords, SAM mask cut inside it, head
  tilted by mediapipe eye-tilt. Master = 358x734 composite; small = LANCZOS
  downsample to 72x148.

Master first; small is ONLY a downsample of the master.
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
COM = r"D:\ComfyUI-Container\workspace\output"   # clean per-frame batch masks
OUT = os.path.join(WS, "llama-780m", "roach-debug", "batch-v4")
GORILLA_BODY = r"C:\Users\gru\Pictures\loj shavale\gorilla-png-37857.jpg"

# pilot: (frame_tag, comfyui batch mask index)
FRAMES = [("f001", "001"), ("f002", "002")]
os.makedirs(OUT, exist_ok=True)

bl = BASE["left"]    # roach:  center rx ry major_angle eye_tilt
br = BASE["right"]   # gorilla

def eye_mid_and_tilt(lm, W, H):
    e1 = ((lm[33].x*W + lm[133].x*W)/2, (lm[33].y*H + lm[133].y*H)/2)
    e2 = ((lm[362].x*W + lm[263].x*W)/2, (lm[263].y*H + lm[263].y*H)/2)
    tilt = math.degrees(math.atan2(e2[1]-e1[1], e2[0]-e1[0]))
    return (e1[0]+e2[0])/2, (e1[1]+e2[1])/2, tilt

def ellipse_mask(w, h, cx, cy, rx, ry, angle=0.0, blur=3.0):
    """Full-alpha ellipse on an (w,h) L image, optionally rotated."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=255)
    if angle:
        m = m.rotate(angle, center=(cx, cy), resample=Image.BICUBIC)
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m

def cut_head_in_ellipse(frame, sam_a, cx, cy, rx, ry, angle=0.0, pad=1.15):
    """Cut the face: take the SAM mask as alpha, intersect with the baseline
    ellipse (the stable frame). Returns an RGBA crop tightly bounding the
    ellipse window. The face content is positioned so that raw-frame (cx,cy)
    maps to the ellipse center in the crop."""
    x0 = int(cx - rx*pad); y0 = int(cy - ry*pad)
    x1 = int(cx + rx*pad); y1 = int(cy + ry*pad)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(frame.width, x1), min(frame.height, y1)
    crop = frame.crop((x0, y0, x1, y1))
    cw, ch = crop.size
    # alpha = SAM mask (the clean comfy cut) inside the crop window
    a = sam_a[y0:y1, x0:x1].copy()
    # refine: intersect with the baseline ellipse (the frame)
    e = ellipse_mask(cw, ch, cx-x0, cy-y0, rx, ry, angle=angle, blur=2.0)
    ea = np.array(e, dtype=np.float32) / 255.0
    a = (a * ea).astype(np.uint8)
    crop.putalpha(Image.fromarray(a, "L"))
    return crop

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

GORILLA_SMALL = (54, 66)
ROACH_SMALL = (72, 148)

def build_gorilla_v4(frame, sam_a):
    """Face fills the body blue ellipse; SAM mask is the clean cut inside."""
    brc = br["center"]
    head = cut_head_in_ellipse(frame, sam_a, brc[0], brc[1], br["rx"], br["ry"], angle=0.0, pad=1.15)
    body = gorilla_body_tpl.copy()
    # erase the original head inside the blue ellipse
    m = Image.new("L", (GBW, GBH), 255)
    d = ImageDraw.Draw(m)
    d.ellipse([GCX-GRX, GCY-GRY, GCX+GRX, GCY+GRY], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(25))
    a = np.array(body.getchannel("A"), dtype=np.float32)
    body.putalpha(Image.fromarray((a*np.array(m, dtype=np.float32)/255.0).astype(np.uint8), "L"))
    # the head crop is (pad*2*rx, pad*2*ry) around the face center; the body
    # ellipse is (2*GRX, 2*GRY). Scale the head so its ellipse window matches
    # the body ellipse: scale = GRX/(rx*pad) == GRY/(ry*pad) (same pad both).
    # Use the body ellipse radii directly so the face always fills it.
    brc = br["center"]
    scale = min(GRX/(br["rx"]*1.15), GRY/(br["ry"]*1.15))
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    # clip the head to the body ellipse (clean edge, v11b)
    head_a = np.array(head.getchannel("A"), dtype=np.float32)
    # ellipse in the (scaled) head space centered where the face center lands
    fcx, fcy = brc[0] - (brc[0] - br["rx"]*1.15), brc[1] - (brc[1] - br["ry"]*1.15)
    fcx, fcy = fcx*scale, fcy*scale
    e = ellipse_mask(new_w, new_h, fcx, fcy, GRX, GRY, blur=8.0)
    head_a *= np.array(e, dtype=np.float32)/255.0
    head.putalpha(Image.fromarray(head_a.astype(np.uint8), "L"))
    body.alpha_composite(head, (int(GCX-new_w/2), int(GCY-new_h/2)))
    master = tight_crop_alpha(body, thresh=40)
    small = master.resize(GORILLA_SMALL, Image.LANCZOS)
    return master, small

def build_roach_v4(frame, sam_a, roach_tilt):
    """Face at the baseline left ellipse; SAM mask cut inside; tilt applied."""
    blc = bl["center"]
    head = cut_head_in_ellipse(frame, sam_a, blc[0], blc[1], bl["rx"], bl["ry"],
                               angle=bl.get("major_angle_from_vertical_deg", 9.86), pad=1.15)
    if abs(roach_tilt) > 3:
        head = head.rotate(roach_tilt, center=(head.width/2, head.height/2),
                           resample=Image.BICUBIC, expand=False)
    body = roach_body_tpl.copy()
    # scale head so its ellipse (rx*pad, ry*pad window) maps to a head that
    # sits at the approved anchor; target head height = approved 345.
    scale = 345 / head.height
    new_w, new_h = int(head.width*scale), int(head.height*scale)
    head = head.resize((new_w, new_h), Image.LANCZOS)
    hx, hy = RBW // 2, int(RBH * 0.19)
    body.alpha_composite(head, (hx - new_w // 2, hy - new_h // 2))
    master = body
    small = body.resize(ROACH_SMALL, Image.LANCZOS)
    return master, small

# ---------- main ----------
for tag, idx in FRAMES:
    raw_path = os.path.join(RAW_DIR, f"raw_{tag}.png")
    mask_path = os.path.join(COM, f"samtest_batch_{idx}_00001_.png")
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
    _, _, roach_tilt = eye_mid_and_tilt(left_lm, W, H)
    roach_master, roach_small = build_roach_v4(frame, sam_a, roach_tilt)
    gora_master, gora_small = build_gorilla_v4(frame, sam_a)
    roach_master.save(os.path.join(OUT, f"roach_{tag}_master.png"))
    roach_small.save(os.path.join(OUT, f"roach_{tag}.png"))
    gora_master.save(os.path.join(OUT, f"gorilla_{tag}_master.png"))
    gora_small.save(os.path.join(OUT, f"gorilla_{tag}.png"))
    print(f"{tag}: roach {roach_master.size}->{roach_small.size} (tilt {roach_tilt:.1f})  "
          f"gorilla {gora_master.size}->{gora_small.size} (no tilt)")
print("done")
