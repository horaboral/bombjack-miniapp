"""Check what the alpha channels of the two PNGs actually contain,
and whether the black is truly opaque or semi-transparent."""
from PIL import Image
import numpy as np
import os

SRC = r"C:\Users\gru\Pictures\loj shavale"
for name in ["300px-Donkey_Kong.png", "300px-Donkey_Kong2.png"]:
    p = os.path.join(SRC, name)
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    arr = np.array(im)
    a = arr[:, :, 3]
    rgb = arr[:, :, :3]
    print(f"=== {name} {w}x{h} ===")
    print(f"alpha min={a.min()} max={a.max()} mean={a.mean():.1f}")
    # where is it transparent?
    trans = a < 10
    print(f"fully transparent: {trans.sum()} px ({100*trans.sum()/(w*h):.1f}%)")
    # in transparent regions, what color is the rgb? (should be black if flattened)
    if trans.sum() > 100:
        trgb = rgb[trans]
        print(f"rgb in transparent px: median {np.median(trgb, axis=0)} max {trgb.max(axis=0)}")
    # in opaque regions, is the bg black? sample the 4 corners' 10x10
    for (cx, cy, lbl) in [(5,5,"TL"),(w-6,5,"TR"),(5,h-6,"BL"),(w-6,h-6,"BR")]:
        patch = arr[cy:cy+10, cx:cx+10]
        pa = patch[:, :, 3].mean()
        prgb = patch[:, :, :3].reshape(-1,3).mean(axis=0)
        print(f"  {lbl}: alpha={pa:.0f} rgb={prgb.round(1)}")
    # bounding box of opaque content
    opaque = a > 128
    ys, xs = np.where(opaque)
    if len(xs):
        print(f"opaque bbox: x=[{xs.min()},{xs.max()}] y=[{ys.min()},{ys.max()}]  ({xs.max()-xs.min()+1}x{ys.max()-ys.min()+1})")
