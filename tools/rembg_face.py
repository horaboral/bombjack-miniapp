"""Test rembg's face/hair-specific models on the loose crops."""
import os
from PIL import Image
from rembg import new_session, remove

WS = r"D:\dsh workspace\dsh test project"
out = os.path.join(WS, "assets", "faces_alpha")

for model in ("u2net_human_seg", "u2net"):
    try:
        session = new_session(model)
    except Exception as e:
        print(model, "session fail:", e)
        continue
    for name in ("left", "right"):
        src = os.path.join(WS, "assets", "faces", name, "f_027.png")
        fg = remove(Image.open(src).convert("RGB"), session=session)
        a = fg.getchannel("A")
        import numpy as np
        arr = np.array(a)
        print(model, name, "alpha mean:", round(arr.mean()/255, 3), "max frac>0.5:",
              round((arr > 128).mean(), 3))
        fg.save(os.path.join(out, f"{name}_027_{model.replace('-', '_')}.png"))
print("done")
