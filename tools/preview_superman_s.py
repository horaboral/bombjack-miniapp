#!/usr/bin/env python3
"""Preview the new Superman shield logo powerup at several spin phases.

Mirrors the canvas math in drawSupermanS (bombjack.html):
  R = size*0.95 ; z = |cos(rot*0.05)| ; s = R*(0.2+0.8z) ; hgt = R*1.25
  shield = flat top, slanted shoulders, pointy bottom
  S = gold quadratic-curve glyph ; red field ; gold border
  edge sliver visible when z<0.9 (the coin's thickness)
"""
import math
from PIL import Image, ImageDraw

SIZE = 9.0          # game size
SCALE = 28          # upscale for visibility
R = SIZE * 0.95
HGT = R * 1.25

def shield_pts(s):
    # in local units (px), centered at (0,0)
    return [(-s, -HGT*0.62), (s, -HGT*0.62), (s*0.92, -HGT*0.18),
            (0, HGT*1.02), (-s*0.92, -HGT*0.18)]

def s_stroke(sw, sh):
    # sample the single stroked S-curve (top hook -> bottom hook)
    def quad(p0, p1, p2, n=20):
        out = []
        for i in range(n+1):
            t = i/n
            x = (1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t**2*p2[0]
            y = (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t**2*p2[1]
            out.append((x, y))
        return out[1:]  # drop dup start
    pts = [(sw*0.85, -sh*0.85)]
    pts += quad((sw*0.85, -sh*0.85), (-sw*0.95, -sh*1.05), (-sw*0.55, -sh*0.05))
    pts += quad((-sw*0.55, -sh*0.05), (-sw*0.30, sh*0.42), (sw*0.28, sh*0.45))
    pts += quad((sw*0.28, sh*0.45), (sw*0.95, sh*0.48), (sw*0.85, sh*0.95))
    return pts

def draw_one(rot):
    W = H = 150
    img = Image.new('RGBA', (W, H), (10, 14, 24, 255))
    d = ImageDraw.Draw(img)
    z = abs(math.cos(rot * 0.05))
    s = R * (0.2 + 0.8 * z)
    cx, cy = W/2, H/2 + 4
    def T(p): return (cx + p[0]*SCALE, cy + p[1]*SCALE)
    # shield body (red field)
    d.polygon([T(p) for p in shield_pts(s)], fill=(216, 31, 38, 255))
    # gold border (canvas lineWidth = max(0.6, R*0.16*z+0.4) px, at 28x scale)
    d.line([T(p) for p in shield_pts(s)] + [T(shield_pts(s)[0])],
           fill=(242, 194, 0, 255), width=max(2, int((R*0.16*z+0.4)*SCALE)), joint='curve')
    # S glyph (canvas lineWidth = max(1.0, s*0.42) px, at 28x scale)
    sw, sh = s*0.62, HGT*0.30
    pts = [T(p) for p in s_stroke(sw, sh)]
    d.line(pts, fill=(242, 194, 0, 255), width=max(2, int((s*0.42)*SCALE)), joint='curve')
    # edge sliver (the coin's thickness, visible near edge-on)
    if z < 0.9:
        ew = max(0.4, (1-z)*R*0.5)
        x0 = -s - ew if z < 0.5 else s
        d.rectangle([T((x0, -HGT*0.55)), T((x0+ew, HGT*0.45))], fill=(202, 160, 0, 255))
    return img, z, rot

# a row of phases across one spin period (full cos cycle ~ 2pi/0.05 = 125.6)
phases = [0, 12, 25, 38, 50, 63, 75, 88, 100, 113]
imgs = [draw_one(p) for p in phases]
cell = 150
row = Image.new('RGBA', (cell*len(imgs), cell+30), (10, 14, 24, 255))
d = ImageDraw.Draw(row)
for i, (im, z, p) in enumerate(imgs):
    row.paste(im, (i*cell, 0, i*cell + 150, 150))
    d.text((i*cell+6, cell+6), f"r{p} z={z:.2f}", fill=(200,200,200))
row.save('tools/preview_superman_s.png')
print('wrote tools/preview_superman_s.png')
print('phases:', [(p, round(abs(math.cos(p*0.05)),2)) for p in phases])
