#!/usr/bin/env python3
"""Show AgenC logo centered on HDMI framebuffer for 3 seconds."""
import os, sys, struct, mmap, time

logo_path = "/opt/agenc/boot_logo.png"
if not os.path.exists(logo_path):
    sys.exit(0)

try:
    from PIL import Image
except Exception:
    sys.exit(0)

# Read framebuffer info
try:
    with open("/sys/class/graphics/fb0/virtual_size") as f:
        parts = f.read().strip().split(",")
        FB_W, FB_H = int(parts[0]), int(parts[1])
    with open("/sys/class/graphics/fb0/stride") as f:
        FB_STRIDE = int(f.read().strip())
except Exception:
    sys.exit(0)

fb_size = FB_STRIDE * FB_H
fd = os.open("/dev/fb0", os.O_RDWR)
fb = mmap.mmap(fd, fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)

# Clear to black
fb.seek(0)
fb.write(b'\x00' * fb_size)

# Load and scale logo
img = Image.open(logo_path).convert("RGB")
scale = min(FB_W, FB_H) // 3
logo = img.resize((scale, scale), Image.LANCZOS)
ox = (FB_W - scale) // 2
oy = (FB_H - scale) // 2

# Write logo pixels to framebuffer (RGB565 little-endian)
pixels = list(logo.getdata())
for py in range(scale):
    for px in range(scale):
        r, g, b = pixels[py * scale + px]
        if r > 5 or g > 5 or b > 5:
            x = ox + px
            y = oy + py
            if 0 <= x < FB_W and 0 <= y < FB_H:
                c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                off = y * FB_STRIDE + x * 2
                fb[off] = c & 0xFF
                fb[off + 1] = (c >> 8) & 0xFF

# Hold for 3 seconds
time.sleep(3)

fb.close()
os.close(fd)
