"""Extract frame 1 (and a few others for reference) from the source video,
full frame, unmodified, no cropping."""
import os
import mediapipe as mp
import cv2

WS = r"D:\dsh workspace\dsh test project"
VIDEO = r"C:\Users\gru\Pictures\loj shavale\photo_2020-08-01_11-07-30 (2).mp4"
OUT = os.path.join(WS, "assets", "raw")
os.makedirs(OUT, exist_ok=True)

cap = cv2.VideoCapture(VIDEO)
idx = 0
frames_to_save = {0, 17, 36, 52}  # frame 1, 18, 37, 53 (0-based)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    if idx in frames_to_save:
        # cv2 is BGR, convert to RGB for PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        from PIL import Image
        Image.fromarray(frame_rgb).save(os.path.join(OUT, f"raw_f{idx+1:03d}.png"))
        print(f"saved frame {idx+1}: {frame.shape[1]}x{frame.shape[0]}")
    idx += 1
cap.release()
print(f"total frames read: {idx}")
