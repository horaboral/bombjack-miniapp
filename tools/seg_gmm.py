"""GMM-based face segmentation: model the frame as a 2-component Gaussian
mixture in RGB; the component with the larger weight and lower variance is
the wall (uniform). Pixels closer to the face component -> opaque.
Keep the largest connected face component, feather the edge."""
import os
import numpy as np
import cv2
from PIL import Image, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
loose = os.path.join(WS, "assets", "faces")
out = os.path.join(WS, "assets", "faces_alpha")
os.makedirs(out, exist_ok=True)

def segment(arr):
    h, w = arr.shape[:2]
    px = arr.reshape(-1, 3).astype(np.float32)
    # subsample for speed
    idx = np.random.RandomState(0).choice(len(px), size=min(20000, len(px)), replace=False)
    sub = px[idx]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1e-4)
    _, labels, centers = cv2.kmeans(sub, 2, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    # cluster stats
    labels = labels.reshape(-1)
    counts = np.bincount(labels, minlength=2)
    variances = [np.var(sub[labels == k], axis=0).sum() for k in range(2)]
    # wall = higher count AND lower variance
    wall_k = 0
    if counts[1] > counts[0] and variances[1] < variances[0]:
        wall_k = 1
    elif counts[0] > counts[1] and variances[0] < variances[1]:
        wall_k = 0
    else:
        wall_k = int(np.argmin(variances))
    wall_c = centers[wall_k]
    face_c = centers[1 - wall_k]
    # distance to each center for ALL pixels
    d_wall = np.linalg.norm(arr.astype(np.float32) - wall_c, axis=2)
    d_face = np.linalg.norm(arr.astype(np.float32) - face_c, axis=2)
    # alpha: prefer face when d_face < d_wall, ramp over the gap
    gap = d_wall - d_face
    alpha = np.clip(gap / 25.0 + 0.5, 0, 1)
    # harden
    alpha = np.where(alpha > 0.55, 1, 0).astype(np.uint8)
    # largest component
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, k, iterations=2)
    n, labels_c, stats, _ = cv2.connectedComponentsWithStats(alpha, 8)
    if n <= 1:
        return None
    areas = stats[1:, cv2.CC_STAT_AREA]
    best = 1 + int(np.argmax(areas))
    mask = (labels_c == best).astype(np.uint8)
    # feather
    m = Image.fromarray(mask * 255).filter(ImageFilter.GaussianBlur(2.0))
    return Image.fromarray(np.dstack([arr, np.array(m)]), "RGBA")

for name in ("left", "right"):
    for i in (1, 27, 53):
        im = Image.open(os.path.join(loose, name, f"f_{i:03d}.png")).convert("RGB")
        res = segment(np.array(im))
        if res:
            res.save(os.path.join(out, f"{name}_{i:03d}_gmm.png"))
    print(name, "gmm test done")
print("done")
