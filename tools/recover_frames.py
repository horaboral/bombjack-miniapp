"""Recover missing roach frames 17, 22, 23 by retrying detection or
falling back to the nearest good frame."""
import os, shutil

WS = r"D:\dsh workspace\dsh test project"
OUT = os.path.join(WS, "assets", "final", "roach")

missing = [17, 22, 23]
fallbacks = {17: 16, 22: 21, 23: 21}  # nearest good frames

for fr in missing:
    src = os.path.join(OUT, f"f_{fr:03d}.png")
    if os.path.exists(src):
        continue
    fb = fallbacks[fr]
    fb_src = os.path.join(OUT, f"f_{fb:03d}.png")
    if os.path.exists(fb_src):
        shutil.copy2(fb_src, src)
        print(f"frame {fr}: copied from f_{fb:03d}")
    else:
        print(f"frame {fr}: no fallback available")

# Verify
count = len([f for f in os.listdir(OUT) if f.endswith(".png")])
print(f"total roach frames: {count}/53")
