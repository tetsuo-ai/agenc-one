#!/usr/bin/env python3
"""agenc-display - Write to the SPI display.

Usage:
  agenc-display text "Hello World"                  # white text, black bg, centered
  agenc-display text "Hello" --color red --bg blue  # colored
  agenc-display text "Line 1\\nLine 2" --size 24     # multiline, custom size
  agenc-display fill black                          # fill screen with color
  agenc-display fill "#FF0000"                      # fill with hex color
  agenc-display image /path/to/image.png            # show image file
  agenc-display off                                 # backlight off
  agenc-display on                                  # backlight on
  agenc-display led red                             # set RGB LED color
  agenc-display led off                             # LED off
  agenc-display clear                               # black screen
"""

import sys
import os
import struct

sys.path.insert(0, "/opt/agenc")

from WhisPlay import WhisPlayBoard
from PIL import Image, ImageDraw, ImageFont

W, H = 240, 280

COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255),
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 80, 255),
    "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "orange": (255, 165, 0), "purple": (128, 0, 255), "pink": (255, 100, 200),
    "gray": (128, 128, 128), "grey": (128, 128, 128),
}


def parse_color(s):
    s = s.lower().strip()
    if s in COLORS:
        return COLORS[s]
    if s.startswith("#") and len(s) == 7:
        return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
    if "," in s:
        parts = s.split(",")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    return (255, 255, 255)


def render_to_display(board, img):
    """Fast RGB to RGB565 big-endian conversion using struct.pack."""
    img = img.convert("RGB")
    data = img.getdata()
    buf = struct.pack('>' + 'H' * len(data),
        *[((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) for r, g, b in data])
    board.set_backlight(100)
    board.draw_image(0, 0, W, H, buf)


def load_font(size):
    paths = [
        "/opt/agenc/DejaVuSans-Bold.ttf",
        "/data/agenc/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/ttf/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/ttf/DejaVuSans.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def word_wrap(text, font, max_width, draw):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def auto_fit(text, draw, padding):
    """Find the largest font size that fits the text on screen."""
    max_w = W - padding * 2
    max_h = H - padding * 2
    lo, hi = 10, 200
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(mid)
        lines = []
        for paragraph in text.split("\n"):
            lines.extend(word_wrap(paragraph, font, max_w, draw) if paragraph.strip() else [""])
        total_h = 0
        fits = True
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            if lw > max_w:
                fits = False
                break
            total_h += lh
        total_h += max(0, len(lines) - 1) * max(4, mid // 8)
        if total_h > max_h:
            fits = False
        if fits:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def cmd_text(board, args):
    text = args[0] if args else "Hello"
    text = text.replace("\\n", "\n")
    color = (255, 255, 255)
    bg = (0, 0, 0)
    manual_size = None

    i = 1
    while i < len(args):
        if args[i] == "--color" and i + 1 < len(args):
            color = parse_color(args[i + 1])
            i += 2
        elif args[i] == "--bg" and i + 1 < len(args):
            bg = parse_color(args[i + 1])
            i += 2
        elif args[i] == "--size" and i + 1 < len(args):
            manual_size = int(args[i + 1])
            i += 2
        else:
            i += 1

    padding = 12
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    size = manual_size if manual_size else auto_fit(text, draw, padding)
    font = load_font(size)

    # Split by explicit newlines first, then word-wrap each
    max_w = W - padding * 2
    all_lines = []
    for paragraph in text.split("\n"):
        wrapped = word_wrap(paragraph, font, max_w, draw) if paragraph.strip() else [""]
        all_lines.extend(wrapped)

    # Measure lines
    line_heights = []
    line_widths = []
    for line in all_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    spacing = max(4, size // 8)
    total_h = sum(line_heights) + (len(all_lines) - 1) * spacing
    y = (H - total_h) // 2

    for j, line in enumerate(all_lines):
        x = (W - line_widths[j]) // 2
        draw.text((x, y), line, fill=color, font=font)
        y += line_heights[j] + spacing

    render_to_display(board, img)
    print(f"Display: \"{text}\"")


def cmd_fill(board, args):
    color = parse_color(args[0] if args else "black")
    img = Image.new("RGB", (W, H), color)
    render_to_display(board, img)
    print(f"Filled: {color}")


def cmd_image(board, args):
    path = args[0] if args else ""
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)
    img = Image.open(path).convert("RGB")
    img.thumbnail((W, H), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    x = (W - img.width) // 2
    y = (H - img.height) // 2
    canvas.paste(img, (x, y))
    render_to_display(board, canvas)
    print(f"Image: {path} ({img.width}x{img.height})")


def cmd_led(board, args):
    color = args[0].lower() if args else "off"
    if color == "off":
        board.set_rgb(0, 0, 0)
    else:
        r, g, b = parse_color(color)
        board.set_rgb(r, g, b)
    print(f"LED: {color}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    board = WhisPlayBoard()
    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "text":
        cmd_text(board, args)
    elif cmd == "fill":
        cmd_fill(board, args)
    elif cmd == "image":
        cmd_image(board, args)
    elif cmd == "clear":
        cmd_fill(board, ["black"])
    elif cmd == "off":
        board.set_backlight(0)
        print("Backlight off")
    elif cmd == "on":
        board.set_backlight(100)
        print("Backlight on")
    elif cmd == "led":
        cmd_led(board, args)
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: text, fill, image, clear, off, on, led")
        sys.exit(1)


if __name__ == "__main__":
    main()
