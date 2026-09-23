"""Show igol ACTUAL FACES: v4 outputs next to approved baselines."""
import os
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
RD = os.path.join(WS, "llama-780m", "roach-debug")
B4 = os.path.join(RD, "batch-v5")

def cell(im, label, w, h):
    im = im.convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    c = Image.new("RGBA", (w, h + 28), (40, 40, 40, 255))
    c.alpha_composite(im, (0, 28))
    d = ImageDraw.Draw(c)
    d.text((5, 8), label, fill=(255, 255, 0, 255))
    return c

# Row 1: ROACH masters (358x734)
rw, rh = 358, 734
roach_row = Image.new("RGBA", (rw*4 + 20, rh + 28), (15, 15, 15, 255))
roach_items = [
    ("APPROVED baseline (mediapipe f027)", os.path.join(RD, "rebuild_roach_f027_full.png")),
    ("APPROVED v11b SAM roach (f027)", os.path.join(RD, "merged_roach_f027.png")),
    ("v5 ROACH f001 (mine, new)", os.path.join(B4, "roach_f001_master.png")),
    ("v5 ROACH f002 (mine, new)", os.path.join(B4, "roach_f002_master.png")),
]
for i, (lab, p) in enumerate(roach_items):
    roach_row.alpha_composite(cell(Image.open(p), lab, rw, rh), (i*rw + 4, 0))

# Row 2: GORILLA masters (scaled to 270x358)
gw, gh = 270, 358
gorilla_row = Image.new("RGBA", (gw*4 + 20, gh + 28), (15, 15, 15, 255))
gorilla_items = [
    ("APPROVED v11b gorilla", os.path.join(RD, "merged_gorilla_v11b.png")),
    ("APPROVED mediapipe gorilla", os.path.join(RD, "rebuild_gorilla_f027_full.png")),
    ("v5 GORILLA f001 (mine, new)", os.path.join(B4, "gorilla_f001_master.png")),
    ("v5 GORILLA f002 (mine, new)", os.path.join(B4, "gorilla_f002_master.png")),
]
for i, (lab, p) in enumerate(gorilla_items):
    gorilla_row.alpha_composite(cell(Image.open(p), lab, gw, gh), (i*gw + 4, 0))

sheet = Image.new("RGBA", (roach_row.width, roach_row.height + gorilla_row.height + 10), (0, 0, 0, 255))
sheet.alpha_composite(roach_row, (0, 0))
sheet.alpha_composite(gorilla_row, (0, roach_row.height + 10))
sheet.convert("RGB").save(os.path.join(RD, "v5_face_sheet.png"))
print("saved v5_face_sheet.png", sheet.size)
