"""Check the actual formats/alpha of the body files."""
from PIL import Image
import os

BODIES = r"D:\dsh workspace\dsh test project\assets\bodies"
for name in sorted(os.listdir(BODIES)):
    p = os.path.join(BODIES, name)
    im = Image.open(p)
    print(f"{name}: {im.format} {im.mode} {im.size}")
    if "mode" in im.info:
        pass
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        a = im.convert("RGBA").getchannel("A")
        hist = a.histogram()
        fully_trans = hist[0]
        total = im.size[0] * im.size[1]
        print(f"   transparent px: {fully_trans}/{total} ({100*fully_trans/total:.1f}%)")
    else:
        print("   no alpha channel")
