"""Verify the roach frame has transparency (no black square)."""
from PIL import Image
im = Image.open(r"D:\dsh workspace\dsh test project\assets\final_small\roach\f_001.png")
print("mode:", im.mode, "size:", im.size)
a = im.convert("RGBA").getchannel("A")
hist = a.histogram()
total = im.size[0] * im.size[1]
trans = hist[0]
print(f"fully transparent px: {trans}/{total} ({100*trans/total:.1f}%)")
# Corner check
print("corner alpha:", a.getpixel((2, 2)), a.getpixel((im.size[0]-3, 2)),
      a.getpixel((2, im.size[1]-3)), a.getpixel((im.size[0]-3, im.size[1]-3)))
