"""Run MODNet portrait matting on face crops (onnxruntime, CPU)."""
import os
import numpy as np
import onnxruntime as ort
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
model_path = os.path.join(WS, "tools", "modnet.onnx")
out = os.path.join(WS, "assets", "faces_alpha")
os.makedirs(out, exist_ok=True)

session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
inp = session.get_inputs()[0]
outp = session.get_outputs()[0]
print("input:", inp.name, inp.shape, "output:", outp.name, outp.shape)

def matte(img_rgb, size=320):
    im = img_rgb.convert("RGB").resize((size, size), Image.BILINEAR)
    arr = np.array(im).astype(np.float32) / 255.0
    # modnet expects NCHW, RGB, 0..1
    arr = arr.transpose(2, 0, 1)[None, ...]
    alpha = session.run(None, {inp.name: arr})[0][0, 0]
    alpha = (alpha * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(alpha).resize(img_rgb.size, Image.BILINEAR)

for name in ("left", "right"):
    for i in (1, 27, 53):
        img = Image.open(os.path.join(WS, "assets", "faces", name, f"f_{i:03d}.png"))
        a = matte(img)
        rgba = img.convert("RGB").copy()
        rgba.putalpha(a)
        rgba.save(os.path.join(out, f"{name}_{i:03d}_modnet.png"))
    print(name, "modnet done")
print("done")
