"""Verify the v30 gorilla small frame: transparent bg, opaque bbox, face present."""
from PIL import Image
import numpy as np

im = Image.open(r"D:\dsh workspace\dsh test project\assets\final_small\gorilla\f_001.png").convert("RGBA")
arr = np.array(im)
a = arr[:, :, 3]
w, h = im.size
print(f"size: {w}x{h}")
print(f"alpha: min={a.min()} mean={a.mean():.1f}")
print(f"fully transparent: {100*(a<10).sum()/(w*h):.1f}%")
# opaque bbox
opaque = a > 128
ys, xs = np.where(opaque)
print(f"opaque bbox: x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}] ({xs.max()-xs.min()+1}x{ys.max()-ys.min()+1})")
# corner alphas
print("corners:", a[2,2], a[2,w-3], a[h-3,2], a[h-3,w-3])
# face region: should be skin-colored and opaque. Head is upper-left of body.
# sample a patch where the face should be (upper area of opaque bbox)
fy0, fy1 = ys.min(), ys.min() + 30
fx0, fx1 = xs.min() + 5, xs.min() + 40
patch = arr[fy0:fy1, fx0:fx1]
print(f"face-region patch rgb mean: {patch[:, :, :3].reshape(-1,3).mean(axis=0).round(0)}")
print(f"face-region alpha mean: {patch[:, :, 3].mean():.0f}")
