"""Extract all 53 frames from the source video at native 10fps."""
import os
import cv2

WS = r"D:\dsh workspace\dsh test project"
VIDEO = r"C:\Users\gru\Pictures\loj shavale\photo_2020-08-01_11-07-30 (2).mp4"
OUT_DIR = os.path.join(WS, "assets", "raw")

cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"video: {fps} fps, {n} frames")

i = 0
saved = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    if i >= 53:
        break  # only 53 frames
    path = os.path.join(OUT_DIR, f"raw_f{i+1:03d}.png")
    cv2.imwrite(path, frame)
    saved += 1
    i += 1
cap.release()
print(f"saved {saved} frames")
