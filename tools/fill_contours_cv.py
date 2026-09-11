"""Use OpenCV to extract and fill the hand-drawn contours. OpenCV's
morphological closing and findContours may handle gaps better."""
import os
import numpy as np
import cv2
from PIL import Image

WS = r"D:\dsh workspace\dsh test project"
marked_path = os.path.join(WS, "assets", "raw", "faces marked raw_f001.jpg")
img = cv2.imread(marked_path)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
arr = img.astype(np.int16)

# Strict thresholds for the hand-drawn line
# Red line: pure red, R high, G and B very low
red_mask = ((arr[:, :, 0] > 140) & (arr[:, :, 1] < 90) & (arr[:, :, 2] < 90)).astype(np.uint8) * 255
# Blue line: pure blue, B high, R and G low
blue_mask = ((arr[:, :, 2] > 130) & (arr[:, :, 0] < 100) & (arr[:, :, 1] < 120)).astype(np.uint8) * 255

def fill_contour_cv(mask, name):
    print(f"{name}: raw line = {(mask > 127).sum()} px")
    # Morphological closing to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    print(f"  after closing: {(closed > 127).sum()} px")
    
    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"  found {len(contours)} contours")
    if not contours:
        return
    
    # Get the largest contour
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    x, y, w, h = cv2.boundingRect(largest)
    print(f"  largest: area={area:.0f}, bbox=({x},{y},{w},{h})")
    
    if area < 5000:  # Too small, probably noise
        print("  -> contour too small, skipping")
        return
    
    # Fill the largest contour
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, [largest], -1, 255, -1)  # -1 = fill
    print(f"  filled: {(filled > 127).sum()} px")
    
    # Save
    mask_img = Image.fromarray(filled, "L")
    margin = 5
    cx0 = max(0, x - margin); cy0 = max(0, y - margin)
    cx1 = min(arr.shape[1], x + w + margin); cy1 = min(arr.shape[0], y + h + margin)
    cropped = mask_img.crop((cx0, cy0, cx1, cy1))
    cropped.save(os.path.join(WS, "assets", "contours", f"filled_{name}.png"))
    print(f"  saved filled_{name}.png ({cropped.size[0]}x{cropped.size[1]})")
    
    # Debug overlay
    ov = img.copy()
    ov[filled > 127] = [255, 160, 0]
    cv2.imwrite(os.path.join(WS, "assets", "preview", f"fillcheck_{name}.png"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))

fill_contour_cv(red_mask, "left")
fill_contour_cv(blue_mask, "right")
print("done")
