"""Download MediaPipe FaceLandmarker model."""
import urllib.request, os

urls = [
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
]
dst = r"D:\dsh workspace\dsh test project\tools\face_landmarker.task"
if os.path.exists(dst) and os.path.getsize(dst) > 3_000_000:
    print("already have:", os.path.getsize(dst))
else:
    for u in urls:
        try:
            print("trying", u)
            urllib.request.urlretrieve(u, dst)
            print("size:", os.path.getsize(dst))
            if os.path.getsize(dst) > 3_000_000:
                break
        except Exception as e:
            print("fail:", e)
print("final:", os.path.getsize(dst) if os.path.exists(dst) else "missing")
