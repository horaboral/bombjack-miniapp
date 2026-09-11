"""Download the MediaPipe face segmentation task model (long/short hair)."""
import urllib.request, os

url = "https://storage.googleapis.com/mediapipe-models/face_segmenter/face_segmenter/float16/latest/face_segmenter.tflite"
dst = r"D:\dsh workspace\dsh test project\tools\face_segmenter.tflite"
if not os.path.exists(dst):
    print("downloading...")
    urllib.request.urlretrieve(url, dst)
print("size:", os.path.getsize(dst))
