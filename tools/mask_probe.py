"""Probe the combined SAM mask: per-row gap position between the two faces."""
import numpy as np
from PIL import Image

m = np.array(Image.open(r"C:\Users\gru\.openclaw\workspace\multi-model\shared\work\outbox\sam-batch-redo-v2\mask_roach_002_f002.png").convert("L"))
H, W = m.shape
print(f"mask {W}x{H}")
for y in range(200, 800, 25):
    row = m[y] > 12
    xs = np.where(row)[0]
    if len(xs) == 0:
        print(f"y={y:4d}: empty")
        continue
    # find the largest internal gap
    gaps = []
    start = xs[0]
    prev = xs[0]
    for x in xs[1:]:
        if x - prev > 1:
            gaps.append((start, prev, x - prev - 1))
            start = x
        prev = x
    gaps.append((start, prev, 0))
    best = max(gaps, key=lambda g: g[2])
    spans = [(g[0], g[1]) for g in gaps if g[1] - g[0] > 20]
    print(f"y={y:4d}: spans={spans}  best_gap={best[2]}px at x~{best[0]+best[2]//2 if best[2]>0 else '-'}")
