"""Download MODNet portrait matting ONNX model from HuggingFace."""
import urllib.request, os

urls = [
    "https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx",
    "https://huggingface.co/Xenova/modnet/resolve/main/model.onnx",
]
dst = r"D:\dsh workspace\dsh test project\tools\modnet.onnx"
if os.path.exists(dst) and os.path.getsize(dst) > 10_000_000:
    print("already have:", os.path.getsize(dst))
else:
    for u in urls:
        try:
            print("trying", u)
            urllib.request.urlretrieve(u, dst)
            print("size:", os.path.getsize(dst))
            if os.path.getsize(dst) > 10_000_000:
                break
        except Exception as e:
            print("fail:", e)
print("final size:", os.path.getsize(dst) if os.path.exists(dst) else "missing")
