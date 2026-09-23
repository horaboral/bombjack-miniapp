"""Per-row: left-face right-edge (notch position) and right-face left-edge."""
import numpy as np
from PIL import Image

m = np.array(Image.open(r"C:\Users\gru\.openclaw\workspace\multi-model\shared\work\outbox\sam-batch-redo-v2\mask_roach_002_f002.png").convert("L"))
H, W = m.shape
print(f"mask {W}x{H}")
print("y     left_span         right_span")
for y in range(221, 781, 10):
    row = m[y] > 12
    xs = np.where(row)[0]
    if len(xs) == 0:
        continue
    gaps, start, prev = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - prev > 1:
            gaps.append((start, prev, x - prev - 1)); start = x
        prev = x
    gaps.append((start, prev, 0))
    # only keep spans wide enough to be a face
    spans = [(g[0], g[1]) for g in gaps if g[1] - g[0] > 30]
    if len(spans) >= 2:
        print(f"{y:4d}  {spans[0]}   {spans[1]}")
    else:
        # single blob: report left span = up to 400, right = 400..end, and the
        # notch = max x in the left half where the row dips to 0
        print(f"{y:4d}  {spans}  (single blob)")
