"""Find per-half face boxes by skin-tone detection.
Skin: R>95, G>40, B>20, max-min>15, R>G, R>B, |R-G|>15.
For each half, take the union of skin pixels over ALL frames, then a
conservative INTERSECTION-ish core: the bounding box of skin pixels that
are present in >80% of frames (the stable face core)."""
import os
from PIL import Image

out_dir = r"D:\dsh workspace\dsh test project\assets\face_frames"
frames = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
imgs = [Image.open(os.path.join(out_dir, f)).convert("RGB") for f in frames]
W, H = imgs[0].size
N = len(imgs)

def is_skin(p):
    r, g, b = p
    return (r > 95 and g > 40 and b > 20 and
            (max(r,g,b) - min(r,g,b)) > 15 and r > g and r > b and abs(r-g) > 15)

# Downsample 2x for speed
SC = 2
sw, sh = W//SC, H//SC
small = [im.resize((sw, sh), Image.LANCZOS).load() for im in imgs]

# Per-half skin presence histogram
for half, (x0, x1) in (("LEFT", (0, sw//2)), ("RIGHT", (sw//2, sw))):
    hist = {}
    for im in small:
        seen = set()
        for y in range(0, sh, 2):
            for x in range(x0, x1, 2):
                if is_skin(im[x, y]):
                    seen.add((x//4, y//4))  # 8px buckets
        for k in seen:
            hist[k] = hist.get(k, 0) + 1
    # stable = present in >70% of frames
    thresh = 0.70 * N
    stable = [k for k, v in hist.items() if v >= thresh]
    if not stable:
        print(half, "no stable skin"); continue
    xs = [k[0] for k in stable]; ys = [k[1] for k in stable]
    # bucket is 8px (4 small-px = 8 full-px)
    box = (min(xs)*8, min(ys)*8, (max(xs)+1)*8, (max(ys)+1)*8)
    print(f"{half}: stable-skin box (full px) {box}  n_stable={len(stable)}/{len(hist)}")
