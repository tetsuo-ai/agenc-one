#!/usr/bin/env python3
"""
AgenC Display - Using EXACT official WhisPlay driver code
From: https://github.com/PiSugar/Whisplay/blob/main/Driver/WhisPlay.py
"""
import RPi.GPIO as GPIO
import spidev
from PIL import Image
import time
import io
import cairosvg
import subprocess

# LCD parameters - exact from official driver
LCD_WIDTH = 240
LCD_HEIGHT = 280
DC_PIN = 13
RST_PIN = 7
LED_PIN = 15

# RGB LED pins
RED_PIN = 22
GREEN_PIN = 18
BLUE_PIN = 16

# Button pin
BUTTON_PIN = 11

# Setup GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Initialize LCD pins
GPIO.setup([DC_PIN, RST_PIN, LED_PIN], GPIO.OUT)

# Initialize RGB LED pins
GPIO.setup([RED_PIN, GREEN_PIN, BLUE_PIN], GPIO.OUT)
GPIO.output(RED_PIN, GPIO.HIGH)   # OFF (PWM inverted)
GPIO.output(GREEN_PIN, GPIO.HIGH)
GPIO.output(BLUE_PIN, GPIO.HIGH)

# Initialize button
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize SPI - exact from official driver
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 100_000_000  # 100MHz
spi.mode = 0b00

def set_backlight(brightness):
    """Simple backlight control (active LOW)"""
    if brightness == 0:
        GPIO.output(LED_PIN, GPIO.HIGH)  # OFF
    else:
        GPIO.output(LED_PIN, GPIO.LOW)   # ON

def reset_lcd():
    """Reset LCD - exact from official driver"""
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.12)

def send_command(cmd, *args):
    """Send command - exact from official driver"""
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.xfer2([cmd])
    if args:
        GPIO.output(DC_PIN, GPIO.HIGH)
        send_data(list(args))

def send_data(data):
    """Send data - exact from official driver"""
    GPIO.output(DC_PIN, GPIO.HIGH)
    try:
        spi.writebytes2(data)
    except AttributeError:
        max_chunk = 4096
        for i in range(0, len(data), max_chunk):
            spi.writebytes(data[i:i + max_chunk])

def init_display():
    """Initialize display - EXACT from official driver"""
    print("Inicializando display...")

    send_command(0x11)  # Sleep out
    time.sleep(0.12)

    # USE_HORIZONTAL = 1 -> direction = 0xC0
    USE_HORIZONTAL = 1
    direction = {0: 0x00, 1: 0xC0, 2: 0x70, 3: 0xA0}.get(USE_HORIZONTAL, 0x00)
    send_command(0x36, direction)

    send_command(0x3A, 0x05)  # 16-bit color
    send_command(0xB2, 0x0C, 0x0C, 0x00, 0x33, 0x33)  # Porch setting
    send_command(0xB7, 0x35)  # Gate control
    send_command(0xBB, 0x32)  # VCOM setting - official value!
    send_command(0xC2, 0x01)  # VDV and VRH enable
    send_command(0xC3, 0x15)  # VRH set - official value!
    send_command(0xC4, 0x20)  # VDV set
    send_command(0xC6, 0x0F)  # Frame rate
    send_command(0xD0, 0xA4, 0xA1)  # Power control

    # Gamma - exact official values
    send_command(0xE0, 0xD0, 0x08, 0x0E, 0x09, 0x09, 0x05, 0x31, 0x33, 0x48, 0x17, 0x14, 0x15, 0x31, 0x34)
    send_command(0xE1, 0xD0, 0x08, 0x0E, 0x09, 0x09, 0x15, 0x31, 0x33, 0x48, 0x17, 0x14, 0x15, 0x31, 0x34)

    send_command(0x21)  # Display inversion on
    send_command(0x29)  # Display on

    print("Display inicializado!")

def set_window(x0, y0, x1, y1):
    """Set window - exact from official driver for USE_HORIZONTAL=1"""
    send_command(0x2A, x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)
    send_command(0x2B, (y0 + 20) >> 8, (y0 + 20) & 0xFF, (y1 + 20) >> 8, (y1 + 20) & 0xFF)
    send_command(0x2C)

def fill_screen(color):
    """Fill screen with color"""
    set_window(0, 0, LCD_WIDTH - 1, LCD_HEIGHT - 1)
    high = (color >> 8) & 0xFF
    low = color & 0xFF
    buffer = [high, low] * (LCD_WIDTH * LCD_HEIGHT)
    send_data(buffer)

def draw_image(x, y, width, height, pixel_data):
    """Draw image at position"""
    set_window(x, y, x + width - 1, y + height - 1)
    send_data(pixel_data)

def rgb565(r, g, b):
    """Convert RGB888 to RGB565"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def load_and_show_logo():
    """Load AgenC logo and display it"""
    print("Cargando logo...")

    # Convert SVG to PNG
    png_data = cairosvg.svg2png(
        url='/home/sa/AgenC_Logo.svg',
        output_width=200,
        output_height=200,
        background_color='white'
    )

    logo = Image.open(io.BytesIO(png_data)).convert('RGB')

    # Create white background
    img = Image.new('RGB', (LCD_WIDTH, LCD_HEIGHT), (255, 255, 255))

    # Center logo
    x_offset = (LCD_WIDTH - 200) // 2
    y_offset = (LCD_HEIGHT - 200) // 2
    img.paste(logo, (x_offset, y_offset))

    print("Mostrando logo...")

    # Convert to RGB565 pixel data
    pixel_data = []
    for y in range(LCD_HEIGHT):
        for x in range(LCD_WIDTH):
            r, g, b = img.getpixel((x, y))
            color = rgb565(r, g, b)
            pixel_data.append((color >> 8) & 0xFF)
            pixel_data.append(color & 0xFF)

    # Draw full screen
    set_window(0, 0, LCD_WIDTH - 1, LCD_HEIGHT - 1)
    send_data(pixel_data)

    print("Logo mostrado!")

def set_leds_yellow(on=True):
    """Yellow = Red + Green (LEDs are inverted - LOW = ON)"""
    if on:
        GPIO.output(RED_PIN, GPIO.LOW)    # Red ON
        GPIO.output(GREEN_PIN, GPIO.LOW)  # Green ON
        GPIO.output(BLUE_PIN, GPIO.HIGH)  # Blue OFF
    else:
        GPIO.output(RED_PIN, GPIO.HIGH)   # All OFF
        GPIO.output(GREEN_PIN, GPIO.HIGH)
        GPIO.output(BLUE_PIN, GPIO.HIGH)

def play_audio():
    """Play audio file"""
    subprocess.run(['mpg123', '-q', '/home/sa/agenchi.mp3'], stderr=subprocess.DEVNULL)

def main():
    try:
        # Turn backlight OFF initially (like official driver)
        set_backlight(0)

        # Reset and init display
        reset_lcd()
        init_display()

        # Fill with black first (like official driver)
        fill_screen(0)

        # Now turn backlight ON
        set_backlight(100)

        # Show logo
        load_and_show_logo()

        # Button polling loop
        print("Esperando boton (polling)...")
        last_state = GPIO.input(BUTTON_PIN)

        while True:
            current_state = GPIO.input(BUTTON_PIN)

            # Button pressed (HIGH when pressed)
            if current_state == 1 and last_state == 0:
                print("BOTON PRESIONADO!")
                set_leds_yellow(True)
                play_audio()
                set_leds_yellow(False)
                print("Audio terminado")

            last_state = current_state
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        spi.close()
        GPIO.cleanup()

if __name__ == '__main__':
    main()
