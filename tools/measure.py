"""Measure the actual face bbox in the v5 masters to verify sizing."""
import os
import numpy as np
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
RD = os.path.join(WS, "llama-780m", "roach-debug")
B5 = os.path.join(RD, "batch-v6")

for tag in ("f001", "f002"):
    rm = Image.open(os.path.join(B5, f"roach_{tag}_master.png")).convert("RGBA")
    ra = np.array(rm.getchannel("A"))
    # roach body is 358x734; the head occupies the top. Find the face region
    # (alpha > 40) in the top third.
    top = ra[:rm.height//3, :]
    ys, xs = np.where(top > 40)
    if len(xs):
        print(f"roach {tag}: head bbox in master = x[{xs.min()}-{xs.max()}] y[{ys.min()}-{ys.max()}] "
              f"-> w={xs.max()-xs.min()+1} h={ys.max()-ys.min()+1}  (master {rm.size})")

for tag in ("f001", "f002"):
    gm = Image.open(os.path.join(B5, f"gorilla_{tag}_master.png")).convert("RGBA")
    ga = np.array(gm.getchannel("A"))
    ys, xs = np.where(ga > 40)
    print(f"gorilla {tag}: face bbox in master = x[{xs.min()}-{xs.max()}] y[{ys.min()}-{ys.max()}] "
          f"-> w={xs.max()-xs.min()+1} h={ys.max()-ys.min()+1}  (master {gm.size})")

print()
print("v11b approved roach head target: 345px tall (full)")
print("25% rescale roach head target: 259px tall (0.75x)")
print("v11b gorilla: face fills body ellipse rx272 ry396 (1.0x)")
print("25% rescale gorilla: face 1.25x / body 0.75x  (NOT yet applied anywhere)")
