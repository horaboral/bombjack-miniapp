"""Fill the user-drawn contours (red=left, blue=right) to create solid
head masks. The contour is a closed loop; flood-fill from the outside
to find the interior. Save filled masks."""
import os
import numpy as np
from PIL import Image, ImageDraw
from collections import deque

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = Image.open(marked_path).convert("RGB")
arr = np.array(img, dtype=np.int16)
H, W = arr.shape[:2]

# Contour lines
red_mask = (arr[:, :, 0] > 140) & (arr[:, :, 1] < 110) & (arr[:, :, 2] < 110)
blue_mask = (arr[:, :, 2] > 120) & (arr[:, :, 0] < 130) & (arr[:, :, 1] < 130)

def fill_contour(line_mask, name):
    """Flood-fill from the border to find the exterior. The interior is
    the complement of (exterior + line)."""
    H, W = line_mask.shape
    # Exterior: flood-fill from all border pixels that are NOT on the line
    exterior = np.zeros((H, W), dtype=bool)
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if not line_mask[y, x] and not exterior[y, x]:
                exterior[y, x] = True; q.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if not line_mask[y, x] and not exterior[y, x]:
                exterior[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not line_mask[ny, nx] and not exterior[ny, nx]:
                exterior[ny, nx] = True; q.append((ny, nx))
    # Interior = not exterior and not line
    interior = ~exterior & ~line_mask
    # The line itself is part of the mask
    filled = interior | line_mask
    ys, xs = np.nonzero(filled)
    if len(xs) == 0:
        print(f"{name}: empty fill"); return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    print(f"{name}: filled {len(xs)} px, bbox x=[{x0},{x1}] y=[{y0},{y1}] "
          f"w={x1-x0} h={y1-y0} center=({(x0+x1)/2:.0f},{(y0+y1)/2:.0f})")
    mask_img = Image.fromarray((filled * 255).astype(np.uint8), "L")
    margin = 5
    cx0 = max(0, x0 - margin); cy0 = max(0, y0 - margin)
    cx1 = min(W, x1 + margin); cy1 = min(H, y1 + margin)
    cropped = mask_img.crop((cx0, cy0, cx1, cy1))
    cropped.save(os.path.join(WS, "assets", "contours", f"filled_{name}.png"))
    print(f"  saved filled_{name}.png ({cropped.size[0]}x{cropped.size[1]})")
    return filled

fill_contour(red_mask, "left")
fill_contour(blue_mask, "right")
print("done")
