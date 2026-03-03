#!/usr/bin/env python3
"""
WhisPlay Board Driver for AgenC ONE
Uses mmap GPIO (no RPi.GPIO or gpiod dependency) + spidev for ST7789 display.
Compatible with Pi Zero 2W kernel 6.6+.
"""

import os
import mmap
import struct
import time
import spidev

# --- BCM2835/2837 GPIO registers (via /dev/gpiomem) ---
_GPFSEL0 = 0x00
_GPSET0 = 0x1C
_GPCLR0 = 0x28
_GPLEV0 = 0x34
_GPPUD = 0x94
_GPPUDCLK0 = 0x98

# --- Pin mapping (BOARD -> BCM) ---
DC_PIN = 27       # BOARD 13 - Data/Command for LCD
RST_PIN = 4       # BOARD 7  - LCD Reset
LED_PIN = 22      # BOARD 15 - LCD Backlight (active LOW)
RED_PIN = 25      # BOARD 22 - RGB LED Red (active LOW)
GREEN_PIN = 24    # BOARD 18 - RGB LED Green (active LOW)
BLUE_PIN = 23     # BOARD 16 - RGB LED Blue (active LOW)
BUTTON_PIN = 17   # BOARD 11 - Button (pull-up, active HIGH)

# --- Display constants ---
LCD_WIDTH = 240
LCD_HEIGHT = 280


class _GPIO:
    """Minimal mmap-based GPIO for BCM2835/2837."""

    def __init__(self):
        fd = os.open('/dev/gpiomem', os.O_RDWR | os.O_SYNC)
        self._mem = mmap.mmap(fd, 4096, mmap.MAP_SHARED,
                              mmap.PROT_READ | mmap.PROT_WRITE, offset=0)
        os.close(fd)

    def _read32(self, offset):
        self._mem.seek(offset)
        return struct.unpack('<I', self._mem.read(4))[0]

    def _write32(self, offset, value):
        self._mem.seek(offset)
        self._mem.write(struct.pack('<I', value))

    def setup_output(self, pin):
        reg = _GPFSEL0 + (pin // 10) * 4
        shift = (pin % 10) * 3
        val = self._read32(reg)
        val &= ~(7 << shift)
        val |= (1 << shift)  # FSEL = 001 = output
        self._write32(reg, val)

    def setup_input(self, pin, pull_up=False):
        reg = _GPFSEL0 + (pin // 10) * 4
        shift = (pin % 10) * 3
        val = self._read32(reg)
        val &= ~(7 << shift)  # FSEL = 000 = input
        self._write32(reg, val)
        # Set pull-up/down
        pud = 2 if pull_up else 0
        self._write32(_GPPUD, pud)
        time.sleep(0.00001)
        self._write32(_GPPUDCLK0, 1 << pin)
        time.sleep(0.00001)
        self._write32(_GPPUD, 0)
        self._write32(_GPPUDCLK0, 0)

    def high(self, pin):
        self._write32(_GPSET0, 1 << pin)

    def low(self, pin):
        self._write32(_GPCLR0, 1 << pin)

    def read(self, pin):
        return bool(self._read32(_GPLEV0) & (1 << pin))


class WhisPlayBoard:
    """WhisPlay HAT driver: ST7789 display + RGB LED + button."""

    def __init__(self):
        self._gpio = _GPIO()

        # Setup output pins
        for pin in (DC_PIN, RST_PIN, LED_PIN, RED_PIN, GREEN_PIN, BLUE_PIN):
            self._gpio.setup_output(pin)

        # Button as input with pull-up
        self._gpio.setup_input(BUTTON_PIN, pull_up=True)

        # LEDs off (active LOW: HIGH = off)
        self._gpio.high(RED_PIN)
        self._gpio.high(GREEN_PIN)
        self._gpio.high(BLUE_PIN)

        # Backlight off initially
        self._gpio.high(LED_PIN)

        # Init SPI
        self._spi = spidev.SpiDev()
        self._spi.open(0, 0)
        self._spi.max_speed_hz = 62_500_000  # 62.5 MHz (safe for Pi Zero 2W)
        self._spi.mode = 0b00

        # Init display
        self._reset()
        self._init_display()

    # --- SPI helpers ---

    def _send_cmd(self, cmd, *args):
        self._gpio.low(DC_PIN)
        self._spi.xfer2([cmd])
        if args:
            self._gpio.high(DC_PIN)
            self._spi.writebytes2(list(args))

    def _send_data(self, data):
        self._gpio.high(DC_PIN)
        if isinstance(data, (bytes, bytearray)):
            # Send in chunks to avoid SPI buffer limits
            mv = memoryview(data)
            chunk = 4096
            for i in range(0, len(data), chunk):
                self._spi.writebytes2(mv[i:i + chunk])
        else:
            self._spi.writebytes2(data)

    # --- LCD init (ST7789, USE_HORIZONTAL=1) ---

    def _reset(self):
        self._gpio.high(RST_PIN)
        time.sleep(0.1)
        self._gpio.low(RST_PIN)
        time.sleep(0.1)
        self._gpio.high(RST_PIN)
        time.sleep(0.12)

    def _init_display(self):
        self._send_cmd(0x11)  # Sleep out
        time.sleep(0.12)
        self._send_cmd(0x36, 0xC0)  # MADCTL: USE_HORIZONTAL=1
        self._send_cmd(0x3A, 0x05)  # 16-bit color
        self._send_cmd(0xB2, 0x0C, 0x0C, 0x00, 0x33, 0x33)
        self._send_cmd(0xB7, 0x35)
        self._send_cmd(0xBB, 0x32)
        self._send_cmd(0xC2, 0x01)
        self._send_cmd(0xC3, 0x15)
        self._send_cmd(0xC4, 0x20)
        self._send_cmd(0xC6, 0x0F)
        self._send_cmd(0xD0, 0xA4, 0xA1)
        self._send_cmd(0xE0, 0xD0, 0x08, 0x0E, 0x09, 0x09, 0x05,
                        0x31, 0x33, 0x48, 0x17, 0x14, 0x15, 0x31, 0x34)
        self._send_cmd(0xE1, 0xD0, 0x08, 0x0E, 0x09, 0x09, 0x15,
                        0x31, 0x33, 0x48, 0x17, 0x14, 0x15, 0x31, 0x34)
        self._send_cmd(0x21)  # Inversion on
        self._send_cmd(0x29)  # Display on

    def _set_window(self, x0, y0, x1, y1):
        self._send_cmd(0x2A, x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)
        self._send_cmd(0x2B, (y0 + 20) >> 8, (y0 + 20) & 0xFF,
                        (y1 + 20) >> 8, (y1 + 20) & 0xFF)
        self._send_cmd(0x2C)

    # --- Public API ---

    def button_pressed(self):
        """Return True if button is pressed (active HIGH)."""
        return self._gpio.read(BUTTON_PIN)

    def set_backlight(self, brightness):
        """Set backlight. 0=off, >0=on. Active LOW."""
        if brightness == 0:
            self._gpio.high(LED_PIN)
        else:
            self._gpio.low(LED_PIN)

    def set_rgb(self, r, g, b):
        """Set RGB LED. Values 0-255. LEDs are active LOW (inverted)."""
        # Simple threshold: >127 = on
        self._gpio.low(RED_PIN) if r > 127 else self._gpio.high(RED_PIN)
        self._gpio.low(GREEN_PIN) if g > 127 else self._gpio.high(GREEN_PIN)
        self._gpio.low(BLUE_PIN) if b > 127 else self._gpio.high(BLUE_PIN)

    def fill_screen(self, color):
        """Fill screen with RGB565 color."""
        self._set_window(0, 0, LCD_WIDTH - 1, LCD_HEIGHT - 1)
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        buf = bytes([high, low]) * (LCD_WIDTH * LCD_HEIGHT)
        self._send_data(buf)

    def draw_image(self, x, y, width, height, pixel_data):
        """Draw RGB565 pixel data at position."""
        self._set_window(x, y, x + width - 1, y + height - 1)
        self._send_data(pixel_data)
