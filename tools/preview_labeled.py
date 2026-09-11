"""Side-by-side labeled: source video frame + my two face crops, to settle
which face is which for the body mapping."""
from PIL import Image, ImageDraw, ImageFont
import os

WS = r"D:\dsh workspace\dsh test project"
full = Image.open(os.path.join(WS, "assets", "face_frames", "frame_027.png")).convert("RGB")
left = Image.open(os.path.join(WS, "assets", "faces", "left", "f_027.png")).convert("RGB")
right = Image.open(os.path.join(WS, "assets", "faces", "right", "f_027.png")).convert("RGB")

def label(img, text, size=22):
    img = img.copy()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width - 1, size + 6], fill="black")
    d.text((6, 2), text, fill="yellow")
    return img

# draw boxes on the full frame where each crop came from
d = ImageDraw.Draw(full)
d.rectangle([40, 150, 400, 700], outline="lime", width=4)
d.text((44, 152), "LEFT crop (laughing man)", fill="lime")
d.rectangle([420, 170, 800, 720], outline="cyan", width=4)
d.text((424, 172), "RIGHT crop (talking man)", fill="cyan")

full = label(full, "SOURCE FRAME 27 - boxes show crop regions")
left = label(left, "assets/faces/LEFT -> mapped to GORILLA")
right = label(right, "assets/faces/RIGHT -> mapped to COCKROACH")

# stack: full on top, two crops below
W = full.width
panel = Image.new("RGB", (W, full.height + left.height + 16), "black")
panel.paste(full, (0, 0))
panel.paste(left, (0, full.height + 8))
panel.paste(right, (0, full.height + left.height + 24))
panel = panel.resize((W // 2, panel.height // 2), Image.LANCZOS)
panel.save(os.path.join(WS, "assets", "preview", "mapping_check.jpg"), quality=88)
print("mapping_check saved", panel.size)
