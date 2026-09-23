#!/usr/bin/env python3
"""Preview the dead-boss death animation: silhouette (alpha mask) filled with
the animated hell.gif, muppet head centered — exact same cover-fit math as
drawDeadBoss() in bombjack.html. Renders one composite per boss (roach=JOTITO,
gorilla=SOBESINHO) and a side-by-side strip."""
from PIL import Image
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELL = os.path.join(ROOT, 'assets', 'hell.gif')
OUT = os.path.join(ROOT, 'tools', 'preview_hell_death.png')

def load_mask(frame_path):
    """Return (frame_rgba, mask) where mask is a 'L' image (alpha>40 -> 255)."""
    fr = Image.open(frame_path).convert('RGBA')
    a = fr.getchannel('A')
    mask = a.point(lambda v: 255 if v > 40 else 0)
    return fr, mask

def render_dead(frame_path, boss_box, bg=(12, 12, 18, 255), pad=24):
    """boss_box = (bw, bh) in game-dest pixels (what the boss is drawn at).
    Returns an RGBA image of the boss box (+pad) with the hell fill clipped to
    the silhouette, head centered."""
    fr, mask = load_mask(frame_path)
    hell = Image.open(HELL).convert('RGBA')  # first frame of the gif
    bw, bh = boss_box
    # cover-fit the hell gif to the boss box, head (gif center) at boss center
    s = max(bw / hell.width, bh / hell.height)
    dw, dh = hell.width * s, hell.height * s
    # paste the scaled hell onto a transparent canvas the size of the boss box,
    # centered (head ends up at the center of the box)
    fill = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    hell_c = hell.resize((int(round(dw)), int(round(dh))), Image.LANCZOS)
    ox = int(round((bw - dw) / 2))
    oy = int(round((bh - dh) / 2))
    fill.alpha_composite(hell_c, (ox, oy))
    # clip to silhouette: use the frame's mask as the alpha
    fill.putalpha(mask.resize((bw, bh), Image.LANCZOS))
    # compose onto a padded dark canvas for visibility
    out = Image.new('RGBA', (bw + pad * 2, bh + pad * 2), bg)
    out.alpha_composite(fill, (pad, pad))
    return out

def label(img, text):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.text((6, 2), text, fill=(255, 255, 255, 255))
    return img

# Boss draw sizes from the game (bossDrawSize): roach 23x48, gorilla 54x66
roach_box = (23, 48)
gorilla_box = (54, 66)
roach_frame = os.path.join(ROOT, 'assets', 'final_small', 'roach', 'f_001.png')
gorilla_frame = os.path.join(ROOT, 'assets', 'final_small', 'gorilla', 'f_001.png')

# Render at 4x for visibility (boss boxes are tiny in game pixels)
SCALE = 4
def render_scaled(frame, box, scale):
    r = render_dead(frame, (box[0] * scale, box[1] * scale))
    return r

r_roach = render_scaled(roach_frame, roach_box, SCALE)
r_gorilla = render_scaled(gorilla_frame, gorilla_box, SCALE)

# Side-by-side strip with labels
gap = 30
H = max(r_roach.height, r_gorilla.height)
W = r_roach.width + gap + r_gorilla.width + 24
strip = Image.new('RGBA', (W, H), (12, 12, 18, 255))
strip.alpha_composite(r_roach, (12, 0))
strip.alpha_composite(r_gorilla, (12 + r_roach.width + gap, 0))
d = ImageDraw.Draw(strip) if False else None
from PIL import ImageDraw
d = ImageDraw.Draw(strip)
d.text((12, 4), 'JOTITO (roach) dead - hell fill', fill=(255, 80, 80, 255))
d.text((12 + r_roach.width + gap, 4), 'SOBESINHO (gorilla) dead - hell fill', fill=(255, 200, 80, 255))
strip.save(OUT)
print('wrote', OUT, strip.size)
# also save individual crops for clarity
r_roach.convert('RGB').save(os.path.join(ROOT, 'tools', 'preview_roach_dead.png'))
r_gorilla.convert('RGB').save(os.path.join(ROOT, 'tools', 'preview_gorilla_dead.png'))
print('done')
