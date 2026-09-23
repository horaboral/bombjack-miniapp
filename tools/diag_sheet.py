"""Contact sheet: approved baselines vs v3 outputs vs mask diagnostics."""
import os
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
RD = os.path.join(WS, "llama-780m", "roach-debug")
B3 = os.path.join(RD, "batch-v3")
COM = r"D:\ComfyUI-Container\workspace\output"

def load(p, label=None, size=(358, 734)):
    im = Image.open(p).convert("RGBA")
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return im

def cell(im, label, w=358, h=734):
    c = Image.new("RGBA", (w, h + 24), (30, 30, 30, 255))
    c.alpha_composite(im, (0, 24))
    d = ImageDraw.Draw(c)
    d.text((4, 4), label, fill=(255, 255, 0, 255))
    return c

def mask_cell(p, label, w=358, h=734):
    m = Image.open(p).convert("L").resize((w, h), Image.NEAREST)
    c = Image.new("RGBA", (w, h + 24), (30, 30, 30, 255))
    c.paste(m.convert("RGB"), (0, 24))
    d = ImageDraw.Draw(c)
    d.text((4, 4), label, fill=(255, 0, 255, 255))
    return c

# ---- row 1: roach ----
roach_cells = [
    cell(load(os.path.join(RD, "rebuild_roach_f027_full.png")), "BASELINE mediapipe (f027)"),
    cell(load(os.path.join(RD, "merged_roach_f027.png")), "v11b SAM roach (f027)"),
    cell(load(os.path.join(B3, "roach_f002_master.png")), "MY v3 roach (f002)"),
    mask_cell(os.path.join(COM, "samtest_batch_027_00001_.png"), "SAM mask f027 (v11b source)"),
    mask_cell(os.path.join(B3, "..", "mask_f002.png") if os.path.exists(os.path.join(B3, "..", "mask_f002.png")) else r"C:\Users\gru\.openclaw\workspace\multi-model\shared\work\outbox\sam-batch-redo-v2\mask_roach_002_f002.png", "SAM mask f002 (my source)"),
]
row1 = Image.new("RGBA", (358 * 5 + 24, 734 + 24), (10, 10, 10, 255))
for i, c in enumerate(roach_cells):
    row1.alpha_composite(c, (i * 358 + 4, 0))

# ---- row 2: gorilla (scaled to same cell) ----
G = (270, 358)  # gorilla display cell
def gcell(im, label, size=G):
    im2 = im.convert("RGBA")
    if im2.size != size:
        im2 = im2.resize(size, Image.LANCZOS)
    c = Image.new("RGBA", (270, 358 + 24), (30, 30, 30, 255))
    c.alpha_composite(im2, (0, 24))
    d = ImageDraw.Draw(c)
    d.text((4, 4), label, fill=(255, 255, 0, 255))
    return c

gorilla_cells = [
    gcell(Image.open(os.path.join(RD, "merged_gorilla_v11b.png")), "BASELINE v11b gorilla"),
    gcell(Image.open(os.path.join(RD, "rebuild_gorilla_f027_full.png")), "BASELINE mediapipe gorilla"),
    gcell(Image.open(os.path.join(B3, "gorilla_f002_master.png")), "MY v3 gorilla (f002)"),
    gcell(Image.open(os.path.join(B3, "gorilla_f002.png")).resize((270, 358), Image.NEAREST), "MY v3 gorilla 54x66 (3x)"),
    gcell(Image.open(r"C:\Users\gru\Pictures\loj shavale\gorilla-png-37857.jpg"), "GORILLA BODY (blue ellipse)"),
]
row2 = Image.new("RGBA", (270 * 5 + 24, 358 + 24), (10, 10, 10, 255))
for i, c in enumerate(gorilla_cells):
    row2.alpha_composite(c, (i * 270 + 4, 0))

sheet = Image.new("RGBA", (max(row1.width, row2.width), row1.height + row2.height + 8), (0, 0, 0, 255))
sheet.alpha_composite(row1, (0, 0))
sheet.alpha_composite(row2, (0, row1.height + 8))
sheet.convert("RGB").save(os.path.join(RD, "v3_diag_sheet.png"))
print("saved", os.path.join(RD, "v3_diag_sheet.png"), sheet.size)
