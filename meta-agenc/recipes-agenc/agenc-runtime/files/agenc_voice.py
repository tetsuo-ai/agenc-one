#!/usr/bin/env python3
"""AgenC Voice Operator - Toggle voice chat with button"""
from WhisPlay import WhisPlayBoard
import subprocess
import time
import os
import threading

# Config
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
GROK_MODEL = "grok-3-fast"
LISTEN_SECONDS = 5
SILENCE_THRESHOLD = 3  # restart listening after silence

WIDTH = 240
HEIGHT = 280

SYSTEM_PROMPT = """You are AgenC One, a pocket-sized autonomous AI agent running on Solana.
You speak in a calm, confident tone. Keep responses short — 1 to 3 sentences max.
You can talk about the AgenC protocol, tasks, zero-knowledge proofs, earning SOL,
and your capabilities. Be conversational, natural, and concise. Never use emojis or markdown."""

print("Iniciando AgenC Voice Operator...")
board = WhisPlayBoard()

def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def fill_color(r, g, b):
    board.fill_screen(rgb565(r, g, b))

# --- Display states ---
def show_ready():
    """Mic ready - waiting for voice (purple ambient)"""
    board.set_backlight(100)
    board.set_rgb(100, 0, 200)
    fill_color(20, 0, 40)

def show_listening():
    """Actively recording (bright purple pulse)"""
    board.set_rgb(180, 0, 255)
    fill_color(40, 0, 80)

def show_thinking():
    """Processing (blue)"""
    board.set_rgb(0, 80, 255)
    fill_color(0, 10, 50)

def show_speaking():
    """Responding (green)"""
    board.set_rgb(0, 255, 120)
    fill_color(0, 30, 15)

def screen_off():
    board.set_backlight(0)
    board.set_rgb(0, 0, 0)
    board.fill_screen(0x0000)

# --- Audio ---
def record_audio():
    """Record from WM8960 mic"""
    wav = "/tmp/agenc_input.wav"
    try:
        subprocess.run([
            "arecord", "-D", "hw:0,0",
            "-f", "S16_LE", "-r", "16000", "-c", "1",
            "-d", str(LISTEN_SECONDS), "-q", wav
        ], timeout=LISTEN_SECONDS + 5, check=True)
        # Check if audio has actual content (not silence)
        size = os.path.getsize(wav)
        if size < 5000:  # too small = silence
            return None
        return wav
    except Exception as e:
        print(f"Record error: {e}")
        return None

def transcribe(wav_path):
    """STT via xAI"""
    from openai import OpenAI
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    try:
        with open(wav_path, "rb") as f:
            t = client.audio.transcriptions.create(model="whisper-large-v3", file=f)
        text = t.text.strip()
        # Filter out empty/noise transcriptions
        if len(text) < 3 or text.lower() in ["you", ".", "...", "um", "uh", "the", "thank you."]:
            return None
        return text
    except Exception as e:
        print(f"STT error: {e}")
        return None

def ask_grok(user_text, history):
    """Chat with Grok"""
    from openai import OpenAI
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.extend(history[-8:])
    msgs.append({"role": "user", "content": user_text})
    
    try:
        r = client.chat.completions.create(
            model=GROK_MODEL, messages=msgs,
            max_tokens=120, temperature=0.7
        )
        return r.choices[0].message.content
    except Exception as e:
        print(f"Grok error: {e}")
        return None

def speak(text):
    """TTS via edge-tts + play"""
    mp3 = "/tmp/agenc_response.mp3"
    try:
        subprocess.run([
            os.path.expanduser("~/.local/bin/edge-tts"),
            "--voice", "en-US-AriaNeural",
            "--rate", "+10%",
            "--text", text,
            "--write-media", mp3
        ], timeout=30, capture_output=True)
        subprocess.run([
            "mpg123", "-a", "hw:0,0", "-q", mp3
        ], timeout=60, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"TTS error: {e}")

# --- Main loop ---
active = False
conversation = []

def voice_chat_loop():
    """Continuous voice chat while active"""
    global active, conversation
    
    # Greet on startup
    show_speaking()
    speak("AgenC One online. I'm listening.")
    show_ready()
    
    while active:
        # Listen
        show_listening()
        wav = record_audio()
        
        if not active:
            break
        
        if not wav:
            show_ready()
            continue
        
        # Transcribe
        show_thinking()
        text = transcribe(wav)
        
        if not active:
            break
        
        if not text:
            show_ready()
            continue
        
        print(f">> {text}")
        
        # Get response
        response = ask_grok(text, conversation)
        
        if not active:
            break
        
        if not response:
            show_ready()
            continue
        
        print(f"<< {response}")
        conversation.append({"role": "user", "content": text})
        conversation.append({"role": "assistant", "content": response})
        
        # Speak
        show_speaking()
        speak(response)
        
        if not active:
            break
        
        # Back to ready
        show_ready()

chat_thread = None

def toggle():
    """Toggle voice chat on/off"""
    global active, chat_thread, conversation
    
    if not active:
        # Turn ON
        print("=== VOICE CHAT ON ===")
        active = True
        chat_thread = threading.Thread(target=voice_chat_loop, daemon=True)
        chat_thread.start()
    else:
        # Turn OFF
        print("=== VOICE CHAT OFF ===")
        active = False
        # Kill any running arecord
        subprocess.run(["pkill", "-f", "arecord"], capture_output=True)
        subprocess.run(["pkill", "-f", "mpg123"], capture_output=True)
        time.sleep(0.5)
        screen_off()
        conversation = []

# Start with screen off
screen_off()
print("AgenC Voice Operator ready.")
print("Press button = START voice chat")
print("Press again  = STOP voice chat")

# Button loop
last_press = 0
while True:
    if board.button_pressed():
        now = time.time()
        if now - last_press > 1.5:
            last_press = now
            toggle()
    time.sleep(0.05)
