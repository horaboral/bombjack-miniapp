"""Show full-size v5 vs 25% rescale v6 side by side (faces, not masks)."""
import os
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
RD = os.path.join(WS, "llama-780m", "roach-debug")
V5 = os.path.join(RD, "batch-v5")
V6 = os.path.join(RD, "batch-v6")

def cell(im, label, w, h):
    im = im.convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    c = Image.new("RGBA", (w, h + 28), (40, 40, 40, 255))
    c.alpha_composite(im, (0, 28))
    d = ImageDraw.Draw(c)
    d.text((5, 8), label, fill=(255, 255, 0, 255))
    return c

rw, rh = 358, 734
gw, gh = 270, 358
row_w = rw*2 + gw*2 + 24

# Row 1: ROACH full (v5) vs 25% (v6)
roach_row = Image.new("RGBA", (row_w, rh + 28), (15, 15, 15, 255))
roach_row.alpha_composite(cell(Image.open(os.path.join(V5, "roach_f001_master.png")),
    "ROACH f001 FULL (v5, head 345px)", rw, rh), (0, 0))
roach_row.alpha_composite(cell(Image.open(os.path.join(V6, "roach_f001_master.png")),
    "ROACH f001 25% (v6, head 259px)", rw, rh), (rw+8, 0))
roach_row.alpha_composite(cell(Image.open(os.path.join(V5, "roach_f002_master.png")),
    "ROACH f002 FULL (v5)", rw, rh), (rw*2+16, 0))
roach_row.alpha_composite(cell(Image.open(os.path.join(V6, "roach_f002_master.png")),
    "ROACH f002 25% (v6)", rw, rh), (rw*3+24, 0))
# fix width (4 cells)
roach_row = Image.new("RGBA", (rw*4 + 30, rh + 28), (15, 15, 15, 255))
roach_row.alpha_composite(cell(Image.open(os.path.join(V5, "roach_f001_master.png")),
    "ROACH f001 FULL (v5)", rw, rh), (0, 0))
roach_row.alpha_composite(cell(Image.open(os.path.join(V6, "roach_f001_master.png")),
    "ROACH f001 25% (v6)", rw, rh), (rw+8, 0))
roach_row.alpha_composite(cell(Image.open(os.path.join(V5, "roach_f002_master.png")),
    "ROACH f002 FULL (v5)", rw, rh), (rw*2+16, 0))
roach_row.alpha_composite(cell(Image.open(os.path.join(V6, "roach_f002_master.png")),
    "ROACH f002 25% (v6)", rw, rh), (rw*3+24, 0))

# Row 2: GORILLA full (v5) vs 25% (v6)
gorilla_row = Image.new("RGBA", (gw*4 + 30, gh + 28), (15, 15, 15, 255))
gorilla_row.alpha_composite(cell(Image.open(os.path.join(V5, "gorilla_f001_master.png")),
    "GORILLA f001 FULL (v5, 1.0x)", gw, gh), (0, 0))
gorilla_row.alpha_composite(cell(Image.open(os.path.join(V6, "gorilla_f001_master.png")),
    "GORILLA f001 25% (v6, face1.25x body0.75x)", gw, gh), (gw+8, 0))
gorilla_row.alpha_composite(cell(Image.open(os.path.join(V5, "gorilla_f002_master.png")),
    "GORILLA f002 FULL (v5)", gw, gh), (gw*2+16, 0))
gorilla_row.alpha_composite(cell(Image.open(os.path.join(V6, "gorilla_f002_master.png")),
    "GORILLA f002 25% (v6)", gw, gh), (gw*3+24, 0))

sheet = Image.new("RGBA", (max(roach_row.width, gorilla_row.width),
                           roach_row.height + gorilla_row.height + 10), (0,0,0,255))
sheet.alpha_composite(roach_row, (0, 0))
sheet.alpha_composite(gorilla_row, (0, roach_row.height + 10))
sheet.convert("RGB").save(os.path.join(RD, "rescale_sheet.png"))
print("saved rescale_sheet.png", sheet.size)
