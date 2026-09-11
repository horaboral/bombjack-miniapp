"""Pre-process bodies: erase the cartoon head regions to create headless versions.
Saves cockroach_headless.png and gorilla_headless.png in assets/bodies/."""
import os
import numpy as np
from PIL import Image, ImageFilter

WS = r"D:\dsh workspace\dsh test project"
BODIES = os.path.join(WS, "assets", "bodies")

def erase_zone(body_path, out_path, zone_box, blur=10):
    """Erase a rectangular zone from the body (set alpha to 0), with a soft edge."""
    body = Image.open(body_path).convert("RGBA")
    W, H = body.size
    x0, y0, x1, y1 = zone_box
    # Create a mask that is 1 in the zone, 0 outside, with a blurred edge
    mask = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(mask)
    d.rectangle([x0, y0, x1, y1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    m = np.array(mask).astype(np.float32) / 255
    a = np.array(body)
    a[..., 3] = (a[..., 3] * (1 - m)).astype(np.uint8)
    Image.fromarray(a, "RGBA").save(out_path)
    print(f"saved {os.path.basename(out_path)} zone={zone_box} blur={blur}")

# Cockroach: 358x734. The cartoon head is roughly the top 30% (y: 0-250, x: 60-300)
# Erase a generous zone to remove the head, eyes, and antennae bases
erase_zone(
    os.path.join(BODIES, "cockroach_full.png"),
    os.path.join(BODIES, "cockroach_headless.png"),
    (40, 0, 320, 260),  # x0, y0, x1, y1
    blur=12
)

# Gorilla: 300x232. The cartoon head is the top ~40% (y: 0-120, x: 60-240)
erase_zone(
    os.path.join(BODIES, "gorilla_full.png"),
    os.path.join(BODIES, "gorilla_headless.png"),
    (50, 0, 250, 130),
    blur=12
)
print("done")
