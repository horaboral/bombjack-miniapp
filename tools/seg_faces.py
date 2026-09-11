"""Segment faces: flood-fill from borders with wall-color tolerance.

The wall is smooth and uniform. Flood-filling from the 4 borders over
pixels close to the local wall color will stop exactly at the face edge.
We use a per-pixel tolerance based on the sampled corner wall color, then
feather the resulting mask."""
import os
import cv2
import numpy as np
from PIL import Image, ImageFilter

src = r"D:\dsh workspace\dsh test project\assets\faces"
out = r"D:\dsh workspace\dsh test project\assets\faces_alpha"
os.makedirs(out, exist_ok=True)

def wall_ref(arr):
    h, w = arr.shape[:2]
    s = max(10, w // 12)
    patches = [arr[:s, :s], arr[:s, -s:], arr[-s:, :s], arr[-s:, -s:]]
    return np.mean(np.concatenate([p.reshape(-1, 3) for p in patches]), axis=0)

def segment(arr):
    h, w = arr.shape[:2]
    wall = wall_ref(arr)
    # BGR for cv2
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    # distance to wall color (in RGB space)
    d = np.sqrt(((arr.astype(np.float32) - wall) ** 2).sum(axis=2))
    # tolerance: pixels within this distance of the wall are "wall"
    TOL = 55.0
    # Build a binary "wall-like" image for flood fill
    walllike = (d < TOL).astype(np.uint8)
    # Flood fill from all border pixels that are wall-like.
    # cv2.floodFill with a mask: we flood the walllike regions connected to border.
    mask = np.zeros((h + 2, w + 2), np.uint8)
    img_ff = walllike.copy()
    # seed from every border pixel that is wall-like
    for x in range(w):
        for y in (0, h - 1):
            if img_ff[y, x]:
                cv2.floodFill(img_ff, mask, (x, y), 0)
    for y in range(h):
        for x in (0, w - 1):
            if img_ff[y, x]:
                cv2.floodFill(img_ff, mask, (x, y), 0)
    # walllike==0 after flood => connected-to-border wall (background)
    # walllike==1 still => NOT connected to border through wall = face interior wall pockets? 
    # Actually: we set connected wall pixels to 0. Remaining 1s are wall-colored but
    # enclosed (shouldn't happen for a face). The FACE is where original walllike was 0
    # (not wall-colored) OR where we didn't flood (enclosed wall).
    # So face = NOT (flooded background)
    flooded_bg = (1 - img_ff)  # 1 where we flooded (background wall)
    # But only pixels that WERE wall-like and got flooded are bg. 
    # Non-wall-colored pixels (d>=TOL) are face regardless.
    face = ((d >= TOL) | (img_ff == 1)).astype(np.uint8)
    # Wait: img_ff==1 means still wall-like AND not flooded to border => enclosed wall (keep as face? no)
    # Let me reconsider: 
    #   original walllike: 1 = wall-colored
    #   after flood, img_ff: 0 = flooded (border-connected wall = BG), 1 = not flooded
    #   BG = wall-colored AND border-connected = (original walllike==1) AND (img_ff==0)
    #   FACE = everything else
    bg = ((d < TOL) & (img_ff == 0)).astype(np.uint8)
    face = (1 - bg)
    # alpha with soft ramp for AA
    ramp = np.clip((d - (TOL - 25)) / 30, 0, 1)
    alpha = face * ramp
    alpha = np.clip(alpha, 0, 1)
    m = Image.fromarray((alpha * 255).astype(np.uint8))
    m = m.filter(ImageFilter.GaussianBlur(1.5))
    return Image.fromarray(np.dstack([arr, np.array(m)]), "RGBA")

for name in ("left", "right"):
    for i in (0, 27, 53):
        im = Image.open(os.path.join(src, name, f"f_{i:03d}.png")).convert("RGB")
        res = segment(np.array(im))
        res.save(os.path.join(out, f"{name}_{i:03d}_test.png"))
    print(name, "test done")
print("done")
