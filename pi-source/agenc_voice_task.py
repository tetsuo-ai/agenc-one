#!/usr/bin/env python3
"""AgenC Voice Task Operator - Cozmo-style Animated Face Display"""

from WhisPlay import WhisPlayBoard
from PIL import Image, ImageDraw, ImageFont
import subprocess
import time
import os
import sys
import json
import threading
import hashlib
import asyncio
import base64
import struct
import math
import random
import websockets
import speech_recognition as sr

# ============ CONFIG ============
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
GROK_MODEL = "grok-3-fast"
LISTEN_SECONDS = 15
WALLET_PATH = "/home/sa/.agenc/wallet.json"
DEVNET_RPC = "https://api.devnet.solana.com"
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
WS_URL = "wss://api.x.ai/v1/realtime"
VOICE = "Ara"
SAMPLE_RATE = 16000
LOG_FILE = "/tmp/agenc_debug.log"
TASKS_FILE = "/home/sa/.agenc/tasks.json"

W = 240
H = 280

SYSTEM_PROMPT_BASE = """You are AgenC One, an autonomous AI agent device running on Solana.
When the user speaks, you must:
1. Identify if they are requesting a TASK (computation, analysis, question, lookup, creation, etc.)
2. If yes, execute the task and provide a concise result.
3. If it is just conversation, respond naturally.
4. If the user asks about a previously completed task, look at COMPLETED TASKS below and report the result and TX signature.

Always respond in this JSON format:
{"is_task": true/false, "task_description": "short description", "result": "the result", "speak": "what to say (1-2 sentences)"}

Keep results concise. Never use markdown or emojis."""

def load_task_history():
    try:
        with open(TASKS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_task_history(tasks):
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)

def build_system_prompt():
    history = load_task_history()
    prompt = SYSTEM_PROMPT_BASE
    if history:
        prompt += "\nCOMPLETED TASKS (most recent first):\n"
        for t in reversed(history[-20:]):
            desc = t.get("desc", "?")
            result = t.get("result", "?")
            tx = t.get("tx", "?")
            prompt += f"- Task: {desc} | Result: {result} | TX: {tx[:8]}...{tx[-4:]}\n"
    return prompt

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    sys.stdout.flush()
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
            f.flush()
    except:
        pass

try:
    open(LOG_FILE, "w").close()
except:
    pass

log("Iniciando AgenC Voice Task Operator...")
board = WhisPlayBoard()

try:
    FONT_SM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    FONT_MD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
except:
    FONT_SM = ImageFont.load_default()
    FONT_MD = FONT_SM

# ============ STATE ============
task_count = 0
last_tx = None
anim_phase = 0.0
last_blink = time.time()
blink_state = 0.0  # 0=open, 1=closed
next_blink = time.time() + random.uniform(2, 5)

# ============ FACE RENDERER ============
# Cozmo/Vector inspired procedural face

def ease_in_out(t):
    """Smooth easing function."""
    return t * t * (3 - 2 * t)

def draw_rounded_rect(draw, xy, radius, fill):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    if r < 1:
        draw.rectangle(xy, fill=fill)
        return
    # Main body
    draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
    draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
    # Corners
    draw.pieslice([x1, y1, x1 + 2 * r, y1 + 2 * r], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * r, y1, x2, y1 + 2 * r], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * r, x1 + 2 * r, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * r, y2 - 2 * r, x2, y2], 0, 90, fill=fill)

def draw_eye(draw, cx, cy, w, h, corner_r, color=(255, 255, 255)):
    """Draw one eye as a rounded rectangle."""
    if h < 2:
        # Blink line
        draw.rectangle([cx - w // 2, cy - 1, cx + w // 2, cy + 1], fill=color)
        return
    x1 = cx - w // 2
    y1 = cy - h // 2
    x2 = cx + w // 2
    y2 = cy + h // 2
    draw_rounded_rect(draw, [x1, y1, x2, y2], corner_r, fill=color)

def draw_mouth_smile(draw, cx, cy, width, curve, color=(255, 255, 255)):
    """Draw a smile/frown arc."""
    if abs(curve) < 2:
        # Flat line
        draw.line([(cx - width // 2, cy), (cx + width // 2, cy)], fill=color, width=2)
        return
    if curve > 0:
        # Smile
        bbox = [cx - width // 2, cy - curve, cx + width // 2, cy + curve]
        draw.arc(bbox, 0, 180, fill=color, width=2)
    else:
        # Frown
        c = abs(curve)
        bbox = [cx - width // 2, cy - c, cx + width // 2, cy + c]
        draw.arc(bbox, 180, 360, fill=color, width=2)

def draw_mouth_open(draw, cx, cy, width, height, color=(255, 255, 255)):
    """Draw an open mouth (ellipse)."""
    if height < 3:
        draw.line([(cx - width // 2, cy), (cx + width // 2, cy)], fill=color, width=2)
        return
    draw_rounded_rect(draw, [cx - width // 2, cy - height // 2, cx + width // 2, cy + height // 2],
                       min(width, height) // 2, fill=color)

def draw_mouth_wave(draw, cx, cy, width, phase, amplitude, color=(255, 255, 255)):
    """Draw a waveform mouth (for speaking)."""
    points = []
    half_w = width // 2
    for i in range(-half_w, half_w + 1, 2):
        t = i / half_w
        y = int(math.sin(phase + t * 8) * amplitude * (1 - t * t * 0.3))
        points.append((cx + i, cy + y))
    if len(points) > 1:
        draw.line(points, fill=color, width=3)

def draw_thinking_dots(draw, cx, cy, phase, color=(255, 255, 255)):
    """Draw animated thinking dots."""
    for i in range(3):
        delay = i * 0.4
        bounce = max(0, math.sin(phase * 4 - delay)) * 8
        dx = (i - 1) * 16
        r = 4
        draw.ellipse([cx + dx - r, cy - r - int(bounce), cx + dx + r, cy + r - int(bounce)], fill=color)

# Face expression presets
EXPRESSIONS = {
    "idle": {
        "eye_w": 40, "eye_h": 44, "eye_r": 14,
        "eye_spacing": 72, "eye_y": -20,
        "gaze_x": 0, "gaze_y": 0,
        "mouth": "smile", "mouth_w": 36, "mouth_curve": 8,
        "color": (255, 255, 255),
    },
    "listening": {
        "eye_w": 48, "eye_h": 52, "eye_r": 16,
        "eye_spacing": 72, "eye_y": -18,
        "gaze_x": 0, "gaze_y": 0,
        "mouth": "open", "mouth_w": 20, "mouth_h": 12,
        "color": (200, 180, 255),
    },
    "transcribe": {
        "eye_w": 36, "eye_h": 36, "eye_r": 12,
        "eye_spacing": 68, "eye_y": -20,
        "gaze_x": 0, "gaze_y": 0,
        "mouth": "flat", "mouth_w": 30,
        "color": (130, 180, 255),
    },
    "thinking": {
        "eye_w": 44, "eye_h": 24, "eye_r": 10,
        "eye_spacing": 64, "eye_y": -16,
        "gaze_x": 8, "gaze_y": -4,
        "mouth": "dots",
        "color": (255, 200, 100),
    },
    "speaking": {
        "eye_w": 42, "eye_h": 46, "eye_r": 14,
        "eye_spacing": 72, "eye_y": -20,
        "gaze_x": 0, "gaze_y": 0,
        "mouth": "wave", "mouth_w": 50, "mouth_amp": 6,
        "color": (150, 255, 180),
    },
    "chain": {
        "eye_w": 50, "eye_h": 50, "eye_r": 18,
        "eye_spacing": 76, "eye_y": -18,
        "gaze_x": 0, "gaze_y": 0,
        "mouth": "open", "mouth_w": 28, "mouth_h": 16,
        "color": (100, 255, 255),
    },
    "confirmed": {
        "eye_w": 44, "eye_h": 30, "eye_r": 14,
        "eye_spacing": 72, "eye_y": -18,
        "gaze_x": 0, "gaze_y": 0,
        "mouth": "smile", "mouth_w": 44, "mouth_curve": 14,
        "color": (100, 255, 200),
    },
    "error": {
        "eye_w": 38, "eye_h": 28, "eye_r": 8,
        "eye_spacing": 60, "eye_y": -14,
        "gaze_x": 0, "gaze_y": 4,
        "mouth": "smile", "mouth_w": 30, "mouth_curve": -8,
        "color": (255, 80, 80),
    },
}

def render_face(state, phase, subtitle=None, wallet_str="", balance=0.0, tasks=0):
    """Render a full face frame."""
    global blink_state, next_blink, last_blink

    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    expr = EXPRESSIONS.get(state, EXPRESSIONS["idle"])
    color = expr["color"]
    face_cx = W // 2
    face_cy = H // 2 - 20  # Face centered slightly above middle

    # Blink logic
    now = time.time()
    if state in ("idle", "speaking", "confirmed") and now >= next_blink:
        blink_state = 1.0
        last_blink = now
        next_blink = now + random.uniform(2.5, 5.0)
    if blink_state > 0:
        blink_state -= 0.25
        if blink_state < 0:
            blink_state = 0

    # Eye params
    ew = expr["eye_w"]
    eh = expr["eye_h"]
    er = expr["eye_r"]
    spacing = expr["eye_spacing"]
    eye_y_off = expr["eye_y"]
    gx = expr.get("gaze_x", 0)
    gy = expr.get("gaze_y", 0)

    # Apply blink
    actual_eh = int(eh * (1.0 - ease_in_out(blink_state)))

    # Idle saccade (subtle random gaze)
    if state == "idle":
        gx += int(math.sin(phase * 0.7) * 3)
        gy += int(math.cos(phase * 0.9) * 2)

    # Draw eyes
    left_cx = face_cx - spacing // 2 + gx
    right_cx = face_cx + spacing // 2 + gx
    eye_cy = face_cy + eye_y_off + gy

    draw_eye(draw, left_cx, eye_cy, ew, actual_eh, er, color)
    draw_eye(draw, right_cx, eye_cy, ew, actual_eh, er, color)

    # Draw mouth
    mouth_cy = face_cy + 40
    mouth_type = expr.get("mouth", "smile")

    if mouth_type == "smile":
        draw_mouth_smile(draw, face_cx, mouth_cy, expr.get("mouth_w", 36),
                        expr.get("mouth_curve", 8), color)
    elif mouth_type == "open":
        draw_mouth_open(draw, face_cx, mouth_cy, expr.get("mouth_w", 20),
                       expr.get("mouth_h", 12), color)
    elif mouth_type == "wave":
        draw_mouth_wave(draw, face_cx, mouth_cy, expr.get("mouth_w", 50),
                       phase, expr.get("mouth_amp", 6), color)
    elif mouth_type == "dots":
        draw_thinking_dots(draw, face_cx, mouth_cy + 5, phase, color)
    elif mouth_type == "flat":
        draw.line([(face_cx - 15, mouth_cy), (face_cx + 15, mouth_cy)],
                  fill=color, width=2)

    # Status text below face
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=FONT_MD)
        tw = bbox[2] - bbox[0]
        x = max(4, (W - tw) // 2)
        # Dim color for text
        tc = tuple(max(0, c // 3) for c in color)
        draw.text((x, H - 52), subtitle, fill=tc, font=FONT_MD)

    # Bottom info bar
    draw.line([(15, H - 34), (W - 15, H - 34)], fill=(25, 25, 30), width=1)
    if wallet_str:
        draw.text((8, H - 28), wallet_str[:18] + "..", fill=(50, 50, 55), font=FONT_SM)
    info_r = f"{balance:.3f} SOL  T:{tasks}"
    bbox = draw.textbbox((0, 0), info_r, font=FONT_SM)
    draw.text((W - 8 - (bbox[2] - bbox[0]), H - 28), info_r, fill=(50, 50, 55), font=FONT_SM)

    return img

# ============ DISPLAY ============
def render_to_display(img):
    pixels = img.load()
    buf = bytearray(W * H * 2)
    idx = 0
    for y in range(H):
        for x in range(W):
            r, g, b = pixels[x, y]
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf[idx] = (rgb565 >> 8) & 0xFF
            buf[idx + 1] = rgb565 & 0xFF
            idx += 2
    board.set_backlight(100)
    board.draw_image(0, 0, W, H, buf)

def show_face(state, subtitle=None, wallet_str="", balance=0.0, tasks=0):
    """Render and display one face frame."""
    global anim_phase
    img = render_face(state, anim_phase, subtitle, wallet_str, balance, tasks)
    render_to_display(img)
    anim_phase += 0.2

def animate_face(state, duration, subtitle=None, wallet_str="", balance=0.0, tasks=0):
    """Animate face for a duration."""
    t0 = time.time()
    while time.time() - t0 < duration:
        show_face(state, subtitle, wallet_str, balance, tasks)
        time.sleep(0.07)

def set_led(state):
    """Set RGB LED to match face state."""
    color = EXPRESSIONS.get(state, EXPRESSIONS["idle"])["color"]
    # Dim the LED a bit
    board.set_rgb(color[0] // 3, color[1] // 3, color[2] // 3)

def screen_off():
    board.set_backlight(0)
    board.set_rgb(0, 0, 0)
    board.fill_screen(0x0000)

# ============ SOLANA ============
def load_or_create_wallet():
    from solders.keypair import Keypair
    os.makedirs(os.path.dirname(WALLET_PATH), exist_ok=True)
    if os.path.exists(WALLET_PATH):
        with open(WALLET_PATH, "r") as f:
            secret = json.load(f)
        kp = Keypair.from_bytes(bytes(secret))
        log(f"Wallet: {kp.pubkey()}")
        return kp
    kp = Keypair()
    with open(WALLET_PATH, "w") as f:
        json.dump(list(bytes(kp)), f)
    os.chmod(WALLET_PATH, 0o600)
    log(f"Wallet created: {kp.pubkey()}")
    return kp

def get_balance(wallet):
    from solana.rpc.api import Client
    try:
        return Client(DEVNET_RPC).get_balance(wallet.pubkey()).value / 1e9
    except:
        return 0.0

def write_memo_tx(wallet, memo_text):
    from solana.rpc.api import Client
    from solders.transaction import Transaction
    from solders.message import Message
    from solders.instruction import Instruction, AccountMeta
    from solders.pubkey import Pubkey
    client = Client(DEVNET_RPC)
    memo_program = Pubkey.from_string(MEMO_PROGRAM_ID)
    ix = Instruction(memo_program, memo_text.encode("utf-8")[:566],
        [AccountMeta(wallet.pubkey(), is_signer=True, is_writable=True)])
    bh = client.get_latest_blockhash().value.blockhash
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), bh)
    tx = Transaction.new_unsigned(msg)
    tx.sign([wallet], bh)
    return str(client.send_transaction(tx).value)

# ============ AUDIO ============
def record_audio():
    """Record with silence detection - stops after 4s of silence."""
    wav = "/tmp/agenc_input.wav"
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.pause_threshold = 4.0      # 4s silence = done
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 1.0
    try:
        mic = sr.Microphone(sample_rate=16000)
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=LISTEN_SECONDS, phrase_time_limit=30)
        with open(wav, "wb") as f:
            f.write(audio.get_wav_data())
        if os.path.getsize(wav) < 5000:
            return None
        return wav
    except sr.WaitTimeoutError:
        return None
    except Exception as e:
        log(f"Record error: {e}")
        # Fallback to fixed arecord
        try:
            subprocess.run(["arecord", "-D", "plughw:0,0", "-f", "S16_LE",
                "-r", "16000", "-c", "1", "-d", "10", "-q", wav],
                timeout=15, check=True)
            if os.path.getsize(wav) < 5000:
                return None
            return wav
        except:
            return None

def transcribe(wav_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio).strip()
        return text if len(text) >= 3 else None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        log(f"STT error: {e}")
        return None

def ask_grok(user_text, history):
    from openai import OpenAI
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    msgs = [{"role": "system", "content": build_system_prompt()}]
    msgs.extend(history[-8:])
    msgs.append({"role": "user", "content": user_text})
    try:
        r = client.chat.completions.create(model=GROK_MODEL, messages=msgs,
            max_tokens=300, temperature=0.7)
        content = r.choices[0].message.content
        try:
            return json.loads(content)
        except:
            return {"is_task": False, "task_description": "", "result": content, "speak": content[:200]}
    except Exception as e:
        log(f"Grok error: {e}")
        return None

# ============ xAI REALTIME TTS ============
def pcm16_to_wav(pcm_data, sample_rate):
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_data)
    wav = bytearray()
    wav.extend(b'RIFF')
    wav.extend(struct.pack('<I', 36 + data_size))
    wav.extend(b'WAVE')
    wav.extend(b'fmt ')
    wav.extend(struct.pack('<I', 16))
    wav.extend(struct.pack('<H', 1))
    wav.extend(struct.pack('<H', num_channels))
    wav.extend(struct.pack('<I', sample_rate))
    wav.extend(struct.pack('<I', byte_rate))
    wav.extend(struct.pack('<H', block_align))
    wav.extend(struct.pack('<H', bits_per_sample))
    wav.extend(b'data')
    wav.extend(struct.pack('<I', data_size))
    wav.extend(pcm_data)
    return bytes(wav)

async def xai_tts(text):
    audio_chunks = []
    try:
        async with websockets.connect(
            WS_URL, additional_headers={"Authorization": f"Bearer {XAI_API_KEY}"},
            ping_interval=20, close_timeout=5,
        ) as ws:
            for _ in range(3):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    if data.get("type") in ("session.created", "conversation.created"):
                        continue
                    break
                except asyncio.TimeoutError:
                    break
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "voice": VOICE, "modalities": ["text", "audio"],
                    "turn_detection": None,
                    "audio": {"output": {"format": {"type": "audio/pcm", "rate": SAMPLE_RATE}}},
                    "instructions": "You are a text-to-speech engine. Read aloud the exact text the user provides. Do NOT add any words."
                }
            }))
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                if json.loads(msg).get("type") == "error":
                    return None
            except asyncio.TimeoutError:
                pass
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {"type": "message", "role": "user",
                         "content": [{"type": "input_text", "text": text}]}
            }))
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {"modalities": ["text", "audio"]}
            }))
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(msg)
                    mt = data.get("type", "")
                    if "audio" in mt and "delta" in mt and "transcript" not in mt:
                        raw = data.get("delta", "")
                        pad = len(raw) % 4
                        if pad:
                            raw += "=" * (4 - pad)
                        audio_chunks.append(base64.b64decode(raw))
                    elif mt == "response.done":
                        break
                    elif mt == "error":
                        break
                except asyncio.TimeoutError:
                    if audio_chunks:
                        break
                    return None
        if not audio_chunks:
            return None
        pcm = b''.join(audio_chunks)
        wav_path = "/tmp/agenc_response.wav"
        with open(wav_path, "wb") as f:
            f.write(pcm16_to_wav(pcm, SAMPLE_RATE))
        log(f"TTS: {len(pcm)/(SAMPLE_RATE*2):.1f}s")
        return wav_path
    except Exception as e:
        log(f"TTS error: {e}")
        return None

def speak(text):
    log(f"speak: '{text[:50]}...'")
    try:
        wav_path = asyncio.run(xai_tts(text))
        if wav_path and os.path.exists(wav_path):
            subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path],
                timeout=60, stderr=subprocess.DEVNULL)
            return
    except Exception as e:
        log(f"TTS failed: {e}")
    log("Fallback: edge-tts")
    mp3 = "/tmp/agenc_response.mp3"
    try:
        subprocess.run([os.path.expanduser("~/.local/bin/edge-tts"),
            "--voice", "en-US-AriaNeural", "--rate", "+10%",
            "--text", text, "--write-media", mp3], timeout=30, capture_output=True)
        subprocess.run(["mpg123", "-a", "hw:0,0", "-q", mp3],
            timeout=60, stderr=subprocess.DEVNULL)
    except Exception as e:
        log(f"Edge-TTS error: {e}")

# ============ MAIN LOOP ============
# This replaces everything from "# ============ MAIN LOOP ============" to end of file

SLEEP_TIMEOUT = 600  # 10 minutes

conversation = []
wallet = None
task_count = 0
last_tx = None

def get_info():
    pub = str(wallet.pubkey()) if wallet else "none"
    bal = get_balance(wallet) if wallet else 0.0
    return pub, bal

def do_one_cycle():
    """Execute one full listen-think-speak cycle. Returns True if task was processed."""
    global conversation, task_count, last_tx
    pub, bal = get_info()

    # Listen - animate face while recording (with silence detection)
    log("Listening...")
    set_led("listening")
    record_result = [None]
    def record_call():
        record_result[0] = record_audio()
    rt = threading.Thread(target=record_call, daemon=True)
    rt.start()
    while rt.is_alive():
        show_face("listening", "Speak now...", pub, bal, task_count)
        time.sleep(0.07)
    rt.join()
    wav_path = record_result[0]
    if not wav_path:
        return False

    # Transcribe
    log("Transcribing...")
    set_led("transcribe")
    show_face("transcribe", "Processing...", pub, bal, task_count)
    text = transcribe(wav_path)
    if not text:
        log("No speech")
        return False
    log(f">> {text}")
    animate_face("transcribe", 0.8, '"' + text[:24] + '..."', pub, bal, task_count)

    # Grok thinking
    log("Asking Grok...")
    set_led("thinking")
    grok_result = [None]
    def grok_call():
        grok_result[0] = ask_grok(text, conversation)
    gt = threading.Thread(target=grok_call, daemon=True)
    gt.start()
    while gt.is_alive():
        show_face("thinking", text[:24] + "...", pub, bal, task_count)
        time.sleep(0.07)
    gt.join()

    response = grok_result[0]
    if not response:
        set_led("error")
        animate_face("error", 1.5, "Grok unavailable", pub, bal, task_count)
        return False

    is_task = response.get("is_task", False)
    task_desc = response.get("task_description", "")
    result = response.get("result", "")
    speak_text = response.get("speak", result[:200])
    log(f"Task: {is_task} | {task_desc}")
    conversation.append({"role": "user", "content": text})
    conversation.append({"role": "assistant", "content": json.dumps(response)})

    # On-chain
    if is_task and wallet:
        set_led("chain")
        task_hash = hashlib.sha256((task_desc + ":" + result).encode()).hexdigest()[:16]
        memo = json.dumps({"p":"agenc-v1","agent":"AgenC-One","act":"task_complete",
            "task":task_desc[:100],"hash":task_hash,"t":int(time.time())}, separators=(",",":"))
        tx_result = [None]
        def tx_call():
            try:
                tx_result[0] = write_memo_tx(wallet, memo)
            except Exception as e:
                log(f"TX error: {e}")
        tt = threading.Thread(target=tx_call, daemon=True)
        tt.start()
        while tt.is_alive():
            show_face("chain", "Writing to chain...", pub, bal, task_count)
            time.sleep(0.07)
        tt.join()
        if tx_result[0]:
            task_count += 1
            last_tx = tx_result[0]
            log(f"TX: {last_tx}")
            short = last_tx[:8] + "..." + last_tx[-6:]
            set_led("confirmed")
            animate_face("confirmed", 2.0, short, pub, bal, task_count)
            speak_text += ". Task recorded on chain."
        else:
            set_led("error")
            animate_face("error", 1.0, "TX failed", pub, bal, task_count)

    # Speak
    log("Speaking...")
    set_led("speaking")
    speak_done = [False]
    def speak_call():
        speak(speak_text)
        speak_done[0] = True
    st = threading.Thread(target=speak_call, daemon=True)
    st.start()
    while not speak_done[0]:
        show_face("speaking", speak_text[:24] + "...", pub, bal, task_count)
        time.sleep(0.07)
    st.join()

    return True

def go_sleep():
    """Enter sleep mode - screen off, LED off."""
    log("=== SLEEP ===")
    subprocess.run(["pkill", "-f", "arecord"], capture_output=True)
    subprocess.run(["pkill", "-f", "aplay"], capture_output=True)
    subprocess.run(["pkill", "-f", "mpg123"], capture_output=True)
    screen_off()

def wake_up():
    """Wake from sleep - show face, play greeting."""
    global conversation
    log("=== WAKE ===")
    pub, bal = get_info()
    conversation = []
    set_led("speaking")
    show_face("speaking", "Waking up...", pub, bal, task_count)
    speak("AgenC One online. Voice to chain active.")
    time.sleep(0.3)

# ============ BOOT ============
log("Loading wallet...")
wallet = load_or_create_wallet()
bal = get_balance(wallet)
pub = str(wallet.pubkey())
log(f"Balance: {bal} SOL")

show_face("idle", "Loading...", pub, bal, task_count)
log("=== Ready ===")

# Initial greeting
set_led("speaking")
show_face("speaking", "Initializing...", pub, bal, task_count)
speak("AgenC One online. Press button to speak.")
time.sleep(0.5)

# Show idle face
set_led("idle")
show_face("idle", "Press button...", pub, bal, task_count)

last_interaction = time.time()
sleeping = False

log("=== Waiting for button ===")

while True:
    # Check button
    pressed = board.button_pressed()

    if pressed:
        if sleeping:
            wake_up()
            sleeping = False

        last_interaction = time.time()
        pub, bal = get_info()

        # Do one listen-think-speak cycle
        did_task = do_one_cycle()

        # Back to idle face
        set_led("idle")
        show_face("idle", "Press button...", pub, bal, task_count)

        # Debounce - wait for button release
        while board.button_pressed():
            time.sleep(0.05)
        time.sleep(0.3)

    elif not sleeping:
        # Check sleep timeout
        if time.time() - last_interaction > SLEEP_TIMEOUT:
            go_sleep()
            sleeping = True
        else:
            # Animate idle face while awake
            pub, bal = get_info()
            show_face("idle", "Press button...", pub, bal, task_count)
            time.sleep(0.07)
    else:
        # Sleeping - minimal CPU
        time.sleep(0.1)
