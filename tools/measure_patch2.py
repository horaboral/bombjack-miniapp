"""Measure the headless white patch on both bodies using column scans in
the central band (x=300..500 for roach, x=60..180 for gorilla) to find
the vertical and horizontal extent of the patch."""
import os
import numpy as np
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"

def measure(name, body_path, x_lo, x_hi, white_thresh):
    body = Image.open(body_path).convert("RGB")
    arr = np.array(body, dtype=np.int16)
    H, W = arr.shape[:2]
    band = arr[:, x_lo:x_hi]
    white = band.min(axis=2) > white_thresh
    # Per-row white fraction
    frac = white.mean(axis=1)
    # Patch rows: fraction > 0.5
    rows = np.nonzero(frac > 0.5)[0]
    if len(rows) == 0:
        print(f"{name}: no patch rows found"); return
    y0, y1 = rows.min(), rows.max()
    # Per-column white fraction in patch rows
    colfrac = white[y0:y1+1].mean(axis=0)
    cols = np.nonzero(colfrac > 0.3)[0]
    x0, x1 = cols.min() + x_lo, cols.max() + x_lo
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = x1 - x0, y1 - y0
    print(f"{name}: patch x=[{x0},{x1}] y=[{y0},{y1}] w={w} h={h} center=({cx:.0f},{cy:.0f})")
    ov = body.copy()
    d = ImageDraw.Draw(ov)
    d.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=4)
    d.ellipse([cx - w/2, cy - h/2, cx + w/2, cy + h/2], outline=(0, 200, 0), width=3)
    out = os.path.join(WS, "assets", "preview", f"patch_{name}.png")
    ov.save(out)
    print(f"  saved {out}")

measure("roach", os.path.join(WS, "assets", "bodies", "roach_headless.jpg"), 280, 520, 230)
measure("gorilla", os.path.join(WS, "assets", "bodies", "gorilla_headless.jpg"), 40, 220, 170)
