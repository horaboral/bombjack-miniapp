"""Find stable face regions by analyzing per-block temporal variance.
Faces = regions that change over time (talking/laughing) vs static background.
We also use color: skin tones cluster. Output per-half (left/right) bounding boxes."""
import os
from PIL import Image
import statistics

out_dir = r"D:\dsh workspace\dsh test project\assets\face_frames"
frames = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
imgs = [Image.open(os.path.join(out_dir, f)).convert("RGB") for f in frames]
W, H = imgs[0].size
print("frame size:", W, H, "count:", len(imgs))

# Grid: 20px blocks. For each block compute mean color + variance across frames.
BW = 20
cols, rows = W // BW, H // BW
px = [im.load() for im in imgs]

def block_stats(c, r):
    xs = []
    for im in px:
        # average of 4 samples in the block
        acc = [0, 0, 0]
        for dx in (0, BW//2):
            for dy in (0, BW//2):
                p = im[c*BW+dx, r*BW+dy]
                acc[0] += p[0]; acc[1] += p[1]; acc[2] += p[2]
        xs.append(tuple(v / 4 for v in acc))
    # variance of the summed color
    vals = [x[0]+x[1]+x[2] for x in xs]
    var = statistics.pvariance(vals)
    mean = tuple(sum(ch[i] for ch in xs)/len(xs) for i in range(3))
    return var, mean

# For the left half and right half, find the bounding box of "high variance" blocks
# (faces move), but constrain to a central vertical band where faces live.
for half, (c0, c1) in (("LEFT", (0, cols//2)), ("RIGHT", (cols//2, cols))):
    best = []
    for c in range(c0, c1):
        for r in range(rows//4, 3*rows//4):  # skip extreme top/bottom
            var, mean = block_stats(c, r)
            if var > 30:  # moving content
                best.append((c, r, var, mean))
    if not best:
        print(half, "no moving blocks")
        continue
    cs = [b[0] for b in best]; rs = [b[1] for b in best]
    print(f"{half}: moving-block bbox cols {min(cs)}..{max(cs)} rows {min(rs)}..{max(rs)} "
          f"= px ({min(cs)*BW},{min(rs)*BW})..({(max(cs)+1)*BW},{(max(rs)+1)*BW})  n={len(best)}")

# Save a composite: 3 frames side by side for visual reference (downscaled)
comp = Image.new("RGB", (W, H*3))
for i, f in enumerate((0, 27, 53)):
    comp.paste(imgs[f], (0, i*H))
comp.save(os.path.join(out_dir, "_composite.jpg"), quality=80)
print("composite saved")
