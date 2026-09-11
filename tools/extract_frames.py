"""Extract every frame of the two-guy video at native 800x800."""
import os
from PIL import Image

import subprocess, json, tempfile, shutil

src = r"C:\Users\gru\Pictures\loj shavale\photo_2020-08-01_11-07-30 (2).mp4"
out_dir = r"D:\dsh workspace\dsh test project\assets\face_frames"
os.makedirs(out_dir, exist_ok=True)

# Use ffmpeg to dump all frames as PNG (lossless)
cmd = ["ffmpeg", "-y", "-i", src, f"{out_dir}\\frame_%03d.png"]
r = subprocess.run(cmd, capture_output=True, text=True)
print("ffmpeg exit", r.returncode)
if r.returncode != 0:
    print(r.stderr[-2000:])

frames = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
print(f"{len(frames)} frames extracted")
print("first:", frames[0], "last:", frames[-1])
