"""Downscale final frames to ~3x display size and re-encode as optimized PNG.
Display sizes: roach 24x49, gorilla 24x19. Target: roach 72x147, gorilla 72x57."""
import os
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
FIN = os.path.join(WS, "assets", "final")
TMP = os.path.join(WS, "assets", "final_small")
os.makedirs(os.path.join(TMP, "roach"), exist_ok=True)
os.makedirs(os.path.join(TMP, "gorilla"), exist_ok=True)

targets = {"roach": (72, 147), "gorilla": (72, 57)}
for tag in ("roach", "gorilla"):
    tw, th = targets[tag]
    src_dir = os.path.join(FIN, tag)
    dst_dir = os.path.join(TMP, tag)
    for f in sorted(os.listdir(src_dir)):
        if not f.endswith(".png"):
            continue
        im = Image.open(os.path.join(src_dir, f)).convert("RGBA")
        # Keep aspect ratio, fit within target
        r = min(tw / im.width, th / im.height)
        nw, nh = max(1, int(im.width * r)), max(1, int(im.height * r))
        im = im.resize((nw, nh), Image.LANCZOS)
        im.save(os.path.join(dst_dir, f), optimize=True)
    n = len(os.listdir(dst_dir))
    tot = sum(os.path.getsize(os.path.join(dst_dir, f)) for f in os.listdir(dst_dir)) / 1e6
    print(f"{tag}: {n} frames, {tot:.2f} MB")
print("done")
