"""Measure the black target ellipses on both headless bodies:
dark pixel extent (min/max x/y) per body, plus a per-row profile to
fit an ellipse (center, rx, ry, tilt). Save overlays."""
import os
import numpy as np
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"

def measure(name, body_path):
    body = Image.open(body_path).convert("RGB")
    arr = np.array(body, dtype=np.int16)
    H, W = arr.shape[:2]
    # Black: all channels < 50
    black = arr.max(axis=2) < 50
    # Exclude the outer border of the image (stock-image outline) by
    # ignoring rows/cols where black spans nearly the full width
    ys, xs = np.nonzero(black)
    print(f"{name}: black pixels = {len(xs)}")
    # Cluster: the target ellipse is the largest connected-ish blob.
    # Simple approach: histogram of y, find the dense band.
    if len(xs) == 0:
        return
    print(f"  raw extent: x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}]")
    # Per-row counts
    rowcnt = black.sum(axis=1)
    dense = np.nonzero(rowcnt > 3)[0]
    if len(dense):
        print(f"  dense rows: y=[{dense.min()},{dense.max()}]")
    # For the overlay, mark the dense-region bbox
    mask = black.copy()
    if len(dense):
        m2 = np.zeros_like(black)
        m2[dense.min():dense.max()+1] = mask[dense.min():dense.max()+1]
        ys2, xs2 = np.nonzero(m2)
        # restrict x to the dense columns too
        colcnt = m2.sum(axis=0)
        dcols = np.nonzero(colcnt > 3)[0]
        m3 = np.zeros_like(black)
        m3[dense.min():dense.max()+1, dcols.min():dcols.max()+1] = m2[dense.min():dense.max()+1, dcols.min():dcols.max()+1]
        ys3, xs3 = np.nonzero(m3)
        x0, x1, y0, y1 = xs3.min(), xs3.max(), ys3.min(), ys3.max()
        cx, cy = (x0+x1)/2, (y0+y1)/2
        rx, ry = (x1-x0)/2, (y1-y0)/2
        print(f"  target ellipse: x=[{x0},{x1}] y=[{y0},{y1}] w={x1-x0} h={y1-y0} "
              f"center=({cx:.1f},{cy:.1f}) rx={rx:.1f} ry={ry:.1f}")
        # Fit a proper ellipse to the blob (least squares)
        pts = np.stack([xs3, ys3], axis=1).astype(float)
        X = pts[:, 0]; Y = pts[:, 1]
        A = np.stack([X*X, X*Y, Y*Y, X, Y, np.ones_like(X)], axis=1)
        try:
            sol, *_ = np.linalg.lstsq(A, np.ones(len(X)), rcond=None)
            a, b, c, d, e, f = sol
            # center
            det = b*b - 4*a*c
            cx2 = (2*c*d - b*e) / (4*a*c - b*b)
            cy2 = (2*a*e - b*d) / (4*a*c - b*b)
            # radii via eigen of the quadratic part
            M = np.array([[a, b/2], [b/2, c]])
            w, v = np.linalg.eigh(M)
            # translate to center: constant term
            cc = a*cx2*cx2 + b*cx2*cy2 + c*cy2*cy2 + d*cx2 + e*cy2 + f
            r1 = np.sqrt(-cc / w[0]) if w[0] != 0 else 0
            r2 = np.sqrt(-cc / w[1]) if w[1] != 0 else 0
            theta = np.degrees(np.arctan2(v[1, 0], v[0, 0]))
            print(f"  conic fit: center=({cx2:.1f},{cy2:.1f}) r1={r1:.1f} r2={r2:.1f} theta={theta:.1f}")
        except Exception as ex:
            print(f"  conic fit failed: {ex}")
        ov = body.copy()
        d = ImageDraw.Draw(ov)
        d.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=3)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=(0, 255, 0), width=3)
        ov.save(os.path.join(WS, "assets", "preview", f"target_{name}.png"))
        print(f"  saved target_{name}.png")

measure("roach", os.path.join(WS, "assets", "bodies", "roach_headless.jpg"))
measure("gorilla", os.path.join(WS, "assets", "bodies", "gorilla_headless.jpg"))
