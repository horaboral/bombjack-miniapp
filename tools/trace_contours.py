"""Trace the red (left) and blue (right) hand-drawn contour lines from the
marked image, fit a baseline ellipse to each set of points, and save the
results for the v19 compositor."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
SRC = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
OUT = os.path.join(WS, "tools")

img = Image.open(SRC).convert("RGB")
arr = np.array(img, dtype=np.int16)
R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]

# Red line: strong red, low green/blue
red_mask = (R > 140) & (G < 110) & (B < 110) & (R - G > 60) & (R - B > 60)
# Blue line: strong blue, low red
blue_mask = (B > 120) & (R < 130) & (B - R > 40) & (B - G > 25)

red_pts = np.column_stack(np.nonzero(red_mask)[::-1]).astype(np.float64)  # (x, y)
blue_pts = np.column_stack(np.nonzero(blue_mask)[::-1]).astype(np.float64)
print(f"red pixels: {len(red_pts)}, blue pixels: {len(blue_pts)}")

def fit_ellipse(pts):
    """Algebraic ellipse fit (least squares) to (x, y) points.
    Returns center, rx, ry, rotation (degrees, CCW from x-axis)."""
    x = pts[:, 0]; y = pts[:, 1]
    # Fit: A x^2 + B xy + C y^2 + D x + E y + F = 0
    X = np.column_stack([x*x, x*y, y*y, x, y, np.ones_like(x)])
    # Use SVD for the constrained fit (general conic)
    # For an ellipse, we use the direct least-squares fit with normalization
    U, s, Vt = np.linalg.svd(X, full_matrices=False)
    coef = Vt[-1]
    A, B, C, D, E, F = coef
    # Center
    cx = (B * E - 2 * C * D) / (4 * A * C - B * B)
    cy = (B * D - 2 * A * E) / (4 * A * C - B * B)
    # Radii
    num1 = 2 * (A * E * E + C * D * D + F * B * B - B * D * E - 4 * A * C * F)
    den1a = B * B - 4 * A * C
    den1 = den1a * (A + C)
    rx = np.sqrt(num1 / den1)
    num2 = 2 * (A * E * E + C * D * D + F * B * B - B * D * E - 4 * A * C * F)
    den2a = B * B - 4 * A * C
    den2 = den2a * (A + C)
    ry = np.sqrt(num2 / den2)
    # Rotation: angle of major axis
    if abs(B) < 1e-9:
        theta = 0.0
    else:
        theta = 0.5 * np.degrees(np.arctan2(B, A - C))
    # Decide which axis is major
    if rx < ry:
        rx, ry = ry, rx
        theta += 90.0
    return cx, cy, rx, ry, theta

# Downsample for a more stable fit (every 5th point)
def subsample(pts, n=5):
    if len(pts) <= 200:
        return pts
    idx = np.linspace(0, len(pts) - 1, 200).astype(int)
    return pts[idx]

for name, pts in [("left (red)", red_pts), ("right (blue)", blue_pts)]:
    sp = subsample(pts)
    cx, cy, rx, ry, theta = fit_ellipse(sp)
    print(f"{name}: center=({cx:.1f},{cy:.1f}) rx={rx:.1f} ry={ry:.1f} rot={theta:+.1f} deg")
    # Save the fitted points + ellipse params
    np.save(os.path.join(OUT, f"trace_{name.split()[0]}.npy"), pts)
    params = {"cx": cx, "cy": cy, "rx": rx, "ry": ry, "theta": theta,
              "n_pts": len(pts),
              "bbox": [float(pts[:,0].min()), float(pts[:,1].min()),
                       float(pts[:,0].max()), float(pts[:,1].max())]}
    import json
    with open(os.path.join(OUT, f"ellipse_{name.split()[0]}.json"), "w") as f:
        json.dump(params, f, indent=2)

print("done")
