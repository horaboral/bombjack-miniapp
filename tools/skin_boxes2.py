"""Stricter skin detection + annotated crops for visual verification."""
import os
from PIL import Image, ImageDraw

out_dir = r"D:\dsh workspace\dsh test project\assets\face_frames"
frames = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
imgs = [Image.open(os.path.join(out_dir, f)).convert("RGB") for f in frames]
W, H = imgs[0].size
N = len(imgs)

def is_skin(p):
    r, g, b = p
    # stricter: yellow wall has G ~ R and high B relative; skin has R >> G >> B
    return (r > 120 and g > 50 and b < r - 20 and
            r - g > 25 and g - b > 10 and
            (max(r,g,b) - min(r,g,b)) > 30 and r > g > b)

SC = 2
sw, sh = W//SC, H//SC
small = [im.resize((sw, sh), Image.LANCZOS).load() for im in imgs]

for half, (x0, x1) in (("LEFT", (0, sw//2)), ("RIGHT", (sw//2, sw))):
    hist = {}
    for im in small:
        seen = set()
        for y in range(sh):
            for x in range(x0, x1):
                if is_skin(im[x, y]):
                    seen.add((x//4, y//4))
        for k in seen:
            hist[k] = hist.get(k, 0) + 1
    thresh = 0.80 * N
    stable = [k for k, v in hist.items() if v >= thresh]
    allsk = list(hist.items())
    if not stable:
        print(half, "no stable skin"); continue
    xs = [k[0] for k in stable]; ys = [k[1] for k in stable]
    box = (min(xs)*8, min(ys)*8, (max(xs)+1)*8, (max(ys)+1)*8)
    print(f"{half}: strict-stable box {box}  n={len(stable)}/{len(allsk)}")
    # annotate a mid frame
    mid = imgs[N//2].copy()
    d = ImageDraw.Draw(mid)
    d.rectangle(box, outline="lime", width=6)
    mid.save(os.path.join(out_dir, f"_{half.lower()}_box.jpg"), quality=85)
print("annotated saved")
