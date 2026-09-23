"""Show igol the mask situation: batch mask, hair masks, and the v11b cut."""
import os
from PIL import Image, ImageDraw

WS = r"D:\dsh workspace\dsh test project"
RD = os.path.join(WS, "llama-780m", "roach-debug")
COM = r"D:\ComfyUI-Container\workspace\output"

W, H = 800, 800
def cell(im, label, note=""):
    im = im.convert("RGB") if im.mode != "RGB" else im
    if im.size != (W, H):
        im = im.resize((W, H), Image.NEAREST)
    c = Image.new("RGB", (W, H + 40), (15, 15, 15))
    c.paste(im, (0, 40))
    d = ImageDraw.Draw(c)
    d.text((6, 6), label, fill=(255, 255, 0))
    if note:
        d.text((6, 22), note, fill=(180, 180, 180))
    return c

cells = []
# 1: the batch mask f002 (what my v3 used)
cells.append(cell(Image.open(os.path.join(COM, "samtest_batch_002_00001_.png")),
                  "samtest_batch_002 (f002) — the CLEAN comfy cut I used",
                  "white = face region; note it stops at the hairline"))
# 2: hair2 union (f001 only)
cells.append(cell(Image.open(os.path.join(COM, "sam_hair2_union_00001_.png")),
                  "sam_hair2_union_00001 (f001 ONLY) — hair merged in",
                  "9/17 one-off; there is no per-frame version for the batch"))
# 3: twopass union (f001 only)
cells.append(cell(Image.open(os.path.join(COM, "sam_twopass_union_00001_.png")),
                  "sam_twopass_union_00001 (f001 ONLY)",
                  "another 9/17 one-off hair experiment"))
# 4: batch mask f027 (what v11b used)
cells.append(cell(Image.open(os.path.join(COM, "samtest_batch_027_00001_.png")),
                  "samtest_batch_027 (f027) — the mask v11b gorilla used",
                  "same workflow, different frame"))

# top row
top = Image.new("RGB", (W*2 + 12, H + 40), (0, 0, 0))
top.paste(cells[0], (0, 0)); top.paste(cells[1], (W+8, 0))
bot = Image.new("RGB", (W*2 + 12, H + 40), (0, 0, 0))
bot.paste(cells[2], (0, 0)); bot.paste(cells[3], (W+8, 0))
sheet = Image.new("RGB", (W*2 + 12, (H+40)*2 + 8), (0, 0, 0))
sheet.paste(top, (0, 0)); sheet.paste(bot, (0, H+48))
sheet.save(os.path.join(RD, "mask_show.png"))
print("saved mask_show.png", sheet.size)
