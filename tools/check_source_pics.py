"""Analyze the original Donkey Kong source images: formats, alpha, bg color."""
from PIL import Image
import os

DIR = r"C:\Users\gru\Pictures\loj shavale"
for name in sorted(os.listdir(DIR)):
    if "Donkey" not in name:
        continue
    p = os.path.join(DIR, name)
    im = Image.open(p)
    info = f"{name}: {im.format} {im.mode} {im.size}"
    print(info)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        a = im.convert("RGBA").getchannel("A")
        hist = a.histogram()
        total = im.size[0] * im.size[1]
        print(f"   transparent: {hist[0]}/{total} ({100*hist[0]/total:.1f}%)")
        # corner alphas
        w, h = im.size
        print(f"   corners: {a.getpixel((2,2))} {a.getpixel((w-3,2))} {a.getpixel((2,h-3))} {a.getpixel((w-3,h-3))}")
    else:
        # check corner colors to identify background
        w, h = im.size
        rgb = im.convert("RGB")
        cs = [rgb.getpixel((2, 2)), rgb.getpixel((w-3, 2)),
              rgb.getpixel((2, h-3)), rgb.getpixel((w-3, h-3))]
        print(f"   corner colors: {cs}")
        # how uniform is the bg? sample border pixels
        import numpy as np
        arr = np.array(rgb)
        border = np.concatenate([arr[0, :].reshape(-1, 3), arr[-1, :].reshape(-1, 3),
                                 arr[:, 0].reshape(-1, 3), arr[:, -1].reshape(-1, 3)])
        med = np.median(border, axis=0)
        std = border.std(axis=0)
        print(f"   border median: {med}, std: {std}")
