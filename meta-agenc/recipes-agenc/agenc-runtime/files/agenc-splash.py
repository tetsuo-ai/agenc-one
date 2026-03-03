#!/usr/bin/env python3
"""
AgenC Boot Splash — Logo + loading animation.
- If HDMI connected: show on HDMI only (SPI left for agent runtime)
- If no HDMI: show on SPI display
- Cleans up on SIGTERM (when agent runtime starts)
"""

import os
import sys
import time
import math
import struct
import mmap
import signal

running = True
def _stop(sig, frame):
    global running
    running = False
signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGHUP, _stop)

# ============ HDMI Detection ============
def hdmi_connected():
    try:
        with open("/sys/class/drm/card0-HDMI-A-1/status") as f:
            return f.read().strip() == "connected"
    except Exception:
        return False

use_hdmi = hdmi_connected()
use_spi = not use_hdmi

# ============ RGB565 helper ============
def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# ============ GPIO + SPI (only if needed) ============
_GPFSEL0 = 0x00
_GPSET0 = 0x1C
_GPCLR0 = 0x28

mem = None
spi = None
W, H = 240, 280

if use_spi:
    DC_PIN = 27
    RST_PIN = 4
    LED_PIN = 22

    fd = os.open('/dev/gpiomem', os.O_RDWR | os.O_SYNC)
    mem = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=0)
    os.close(fd)

    def _r32(off):
        mem.seek(off)
        return struct.unpack('<I', mem.read(4))[0]
    def _w32(off, v):
        mem.seek(off)
        mem.write(struct.pack('<I', v))
    def _setup_out(pin):
        reg = _GPFSEL0 + (pin // 10) * 4
        s = (pin % 10) * 3
        v = _r32(reg)
        v &= ~(7 << s)
        v |= (1 << s)
        _w32(reg, v)
    def _high(pin): _w32(_GPSET0, 1 << pin)
    def _low(pin):  _w32(_GPCLR0, 1 << pin)

    import spidev
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 62_500_000
    spi.mode = 0b00

    def cmd(c, *args):
        _low(DC_PIN)
        spi.xfer2([c])
        if args:
            _high(DC_PIN)
            spi.writebytes2(list(args))
    def spi_data(d):
        _high(DC_PIN)
        mv = memoryview(d) if isinstance(d, (bytes, bytearray)) else d
        for i in range(0, len(d), 4096):
            spi.writebytes2(mv[i:i + 4096] if isinstance(d, (bytes, bytearray)) else d[i:i + 4096])
    def set_window(x0, y0, x1, y1):
        cmd(0x2A, x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)
        cmd(0x2B, (y0+20) >> 8, (y0+20) & 0xFF, (y1+20) >> 8, (y1+20) & 0xFF)
        cmd(0x2C)

    for pin in (DC_PIN, RST_PIN, LED_PIN):
        _setup_out(pin)

    # Reset + init ST7789
    _high(RST_PIN); time.sleep(0.1)
    _low(RST_PIN);  time.sleep(0.1)
    _high(RST_PIN); time.sleep(0.12)
    cmd(0x11); time.sleep(0.12)
    cmd(0x36, 0xC0)
    cmd(0x3A, 0x05)
    cmd(0xB2, 0x0C, 0x0C, 0x00, 0x33, 0x33)
    cmd(0xB7, 0x35); cmd(0xBB, 0x32); cmd(0xC2, 0x01)
    cmd(0xC3, 0x15); cmd(0xC4, 0x20); cmd(0xC6, 0x0F)
    cmd(0xD0, 0xA4, 0xA1)
    cmd(0xE0, 0xD0,0x08,0x0E,0x09,0x09,0x05,0x31,0x33,0x48,0x17,0x14,0x15,0x31,0x34)
    cmd(0xE1, 0xD0,0x08,0x0E,0x09,0x09,0x15,0x31,0x33,0x48,0x17,0x14,0x15,0x31,0x34)
    cmd(0x21); cmd(0x29)
    _low(LED_PIN)  # Backlight on

# ============ HDMI Framebuffer ============
FB_W, FB_H, FB_STRIDE = 0, 0, 0
fb_fd = None
fb_mm = None

if use_hdmi:
    try:
        with open("/sys/class/graphics/fb0/virtual_size") as f:
            parts = f.read().strip().split(",")
            FB_W, FB_H = int(parts[0]), int(parts[1])
        with open("/sys/class/graphics/fb0/stride") as f:
            FB_STRIDE = int(f.read().strip())
        fb_size = FB_STRIDE * FB_H
        fb_fd = os.open("/dev/fb0", os.O_RDWR)
        fb_mm = mmap.mmap(fb_fd, fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
        # Clear to black
        fb_mm.seek(0)
        fb_mm.write(b'\x00' * fb_size)
    except Exception:
        fb_mm = None
        use_hdmi = False
        use_spi = True  # Fallback to SPI

def fb_fill_rect(x0, y0, w, h, r, g, b):
    if fb_mm is None:
        return
    c = rgb565(r, g, b)
    pixel = struct.pack('<H', c)
    row = pixel * w
    for y in range(max(0, y0), min(y0 + h, FB_H)):
        off = y * FB_STRIDE + max(0, x0) * 2
        fb_mm[off:off + w * 2] = row

# ============ Load logo ============
logo_loaded = False
spi_logo_buf = bytearray(W * H * 2) if use_spi else None

try:
    from PIL import Image
    logo_path = "/opt/agenc/boot_logo.png"
    if os.path.exists(logo_path):
        img = Image.open(logo_path).convert("RGB")

        if use_spi:
            # Scale to 140x140 centered on 240x280
            spi_logo = img.resize((140, 140), Image.LANCZOS)
            display = Image.new("RGB", (W, H), (0, 0, 0))
            display.paste(spi_logo, ((W - 140) // 2, (H - 140) // 2 - 30))
            idx = 0
            for r, g, b in display.getdata():
                c = rgb565(r, g, b)
                spi_logo_buf[idx] = (c >> 8) & 0xFF
                spi_logo_buf[idx + 1] = c & 0xFF
                idx += 2

        if use_hdmi and fb_mm:
            # Scale logo to 1/3 of screen height, centered
            scale = min(FB_W, FB_H) // 3
            fb_logo = img.resize((scale, scale), Image.LANCZOS)
            fb_logo_x = (FB_W - scale) // 2
            fb_logo_y = (FB_H - scale) // 2 - FB_H // 8
            px = list(fb_logo.getdata())
            for py_i in range(scale):
                for px_i in range(scale):
                    r, g, b = px[py_i * scale + px_i]
                    if r > 10 or g > 10 or b > 10:
                        x = fb_logo_x + px_i
                        y = fb_logo_y + py_i
                        if 0 <= x < FB_W and 0 <= y < FB_H:
                            c = rgb565(r, g, b)
                            off = y * FB_STRIDE + x * 2
                            fb_mm[off] = c & 0xFF
                            fb_mm[off + 1] = (c >> 8) & 0xFF

        logo_loaded = True
except Exception:
    pass

# ============ Spinner rendering ============
def draw_spinner_spi(buf, phase):
    cx, cy = W // 2, H // 2 + 65
    radius = 16
    for i in range(8):
        angle = (2 * math.pi * i / 8) - (math.pi / 2)
        dx = int(cx + radius * math.cos(angle))
        dy = int(cy + radius * math.sin(angle))
        brightness = max(0.15, (math.sin(phase - i * 0.8) + 1) / 2)
        gray = int(255 * brightness)
        c = rgb565(gray, gray, gray)
        ch = (c >> 8) & 0xFF
        cl = c & 0xFF
        for ox in range(-1, 2):
            for oy in range(-1, 2):
                px, py = dx + ox, dy + oy
                if 0 <= px < W and 0 <= py < H:
                    pidx = (py * W + px) * 2
                    buf[pidx] = ch
                    buf[pidx + 1] = cl

def draw_spinner_fb(phase):
    if fb_mm is None:
        return
    cx = FB_W // 2
    cy = FB_H // 2 + FB_H // 6
    radius = 40
    dot_r = 5
    # Clear spinner region
    fb_fill_rect(cx - radius - dot_r - 2, cy - radius - dot_r - 2,
                 (radius + dot_r + 2) * 2, (radius + dot_r + 2) * 2, 0, 0, 0)
    for i in range(8):
        angle = (2 * math.pi * i / 8) - (math.pi / 2)
        dx = int(cx + radius * math.cos(angle))
        dy = int(cy + radius * math.sin(angle))
        brightness = max(0.15, (math.sin(phase - i * 0.8) + 1) / 2)
        gray = int(255 * brightness)
        fb_fill_rect(dx - dot_r, dy - dot_r, dot_r * 2, dot_r * 2, gray, gray, gray)

# ============ Main loop ============
phase = 0.0
while running:
    if use_spi:
        buf = bytearray(spi_logo_buf)
        draw_spinner_spi(buf, phase)
        set_window(0, 0, W - 1, H - 1)
        spi_data(buf)

    if use_hdmi:
        draw_spinner_fb(phase)

    phase += 0.3
    time.sleep(0.05)

# ============ Cleanup on exit ============
if fb_mm:
    try:
        fb_mm.seek(0)
        fb_mm.write(b'\x00' * (FB_STRIDE * FB_H))
        fb_mm.close()
    except Exception:
        pass
if fb_fd is not None:
    try:
        os.close(fb_fd)
    except Exception:
        pass
if spi:
    spi.close()
if mem:
    mem.close()
