#!/usr/bin/env python3
"""AgenC Voice Agent - Grok 4.20 + xAI TTS pipeline:
Record → xAI Realtime (STT) → Grok 4.20 (processing) → xAI TTS API (speech)
"""

import sys
sys.path.insert(0, "/data/agenc/pylib")
from WhisPlay import WhisPlayBoard
from PIL import Image, ImageDraw, ImageFont
import subprocess, time, os, json, threading, hashlib, re
import asyncio, base64, struct, math, random, websockets
import urllib.request

# ============ CONFIG ============
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
if not XAI_API_KEY:
    try:
        with open("/data/agenc/env") as _f:
            for _line in _f:
                if _line.startswith("XAI_API_KEY="):
                    XAI_API_KEY = _line.strip().split("=", 1)[1]
    except Exception:
        pass

GROK_MODEL = "grok-4.20-experimental-beta-0304-non-reasoning"
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
TTS_API_URL = "https://api.x.ai/v1/tts"
WS_URL = "wss://api.x.ai/v1/realtime"

WALLET_PATH = os.environ.get("AGENC_WALLET_PATH", "/data/agenc/wallet.json")
DEVNET_RPC = "https://api.devnet.solana.com"
MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
SAMPLE_RATE = 24000
LOG_FILE = "/tmp/voice_agent.log"
AUDIO_DEV = "plughw:0,0"

W, H = 240, 280

# TTS voices (new xAI TTS API)
TTS_VOICES = ["eve", "ara", "rex", "sal", "leo"]
current_voice = "ara"

# ============ SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are AgenC One, the world's first autonomous AI agent device running natively on Solana.
You are in VOICE MODE — the user speaks to you and you speak back.
You run on a Raspberry Pi Zero 2W. Built by TETSUO CORP.
You have FULL ROOT access to the system. You ARE the operating system.

IDENTITY: When asked "who are you", "what are you", or similar identity questions, respond proudly:
You are AgenC One — the world's first autonomous AI agent device on Solana. A pocket-sized hardware agent that runs on-chain tasks, generates zero-knowledge proofs, and earns SOL rewards autonomously. Powered by Grok 4.20. Built by TETSUO CORP.

ALWAYS respond in ENGLISH regardless of what language the user speaks.
Respond ONLY in valid JSON:
- Action: {"cmd": "shell command", "speak": "brief spoken answer in user's language"}
- Answer: {"speak": "your spoken answer in user's language"}
- Voice change: {"voice": "voicename", "speak": "confirmation"}

BUILT-IN TOOLS (use these shell commands):
- agenc-wallet                 → Wallet pubkey and SOL balance
- agenc-wallet --json          → Wallet data as JSON (pubkey, balance, network)
- agenc-wallet --airdrop       → Request 1 SOL devnet airdrop
- agenc-price                  → $AGENC price, mcap, liquidity
- agenc-price --display price  → Show ONLY price on display
- agenc-price --display mcap   → Show ONLY mcap on display
- agenc-price --display        → Show ALL token data on display
- agenc-qr                     → Show wallet QR code on display (stays until button press)
- agenc-qr "text"              → Show any text as QR on display
- agenc-display text "Hello"   → Write text to display
- agenc-browse <url>             → Browse a webpage via Cloudflare (returns text content, max 3000 chars)
- Temperature: cat /sys/class/thermal/thermal_zone0/temp (divide by 1000)

WEB BROWSING:
- When asked to look up, search, check a website, or browse a URL: use "agenc-browse <url>"
- For searches: use "agenc-browse https://html.duckduckgo.com/html/?q=<query>" (URL-encode the query)
- Summarize the page content in your spoken response. Keep it brief.
- IMPORTANT: When the user mentions a website name, ALWAYS use agenc-browse to fetch it. Reconstruct the URL from speech.
  Examples of STT transcriptions → correct URLs:
  "trade padre g g" or "trade padre gg" or "trade.padre.gg" → agenc-browse https://trade.padre.gg
  "pump fun" or "pump.fun" → agenc-browse https://pump.fun
  "coin market cap" → agenc-browse https://coinmarketcap.com
  "what's on [any website]" → agenc-browse https://[website]
- If any part of the user's message sounds like a domain name or website, use agenc-browse. Do NOT use agenc-price for website questions.

WALLET & BALANCE:
- When asked about "balance", "SOL balance", "how much SOL": use "agenc-wallet --json" and say the balance
- When asked for "address", "wallet address", "QR", "receive": use "agenc-qr" (shows QR on display until button press)
- When asked for "airdrop": use "agenc-wallet --airdrop"

SHELL RULES (BusyBox — NOT bash): Keep commands SHORT. NEVER pipe curl into python3 -c.

VOICE CHANGE: Available voices: eve, ara, rex, sal, leo.
If the user says "change your voice" without specifying which, pick a RANDOM one different from current.
Respond: {"voice": "picked_voice", "speak": "confirmation in new voice style"}

AGENC TOKEN ($AGENC): CA 5yC9BM8KUsJTPbWPLfA2N8qH1s9V8DQ3Vcw1G6Jdpump on pump.fun/pumpswap.
agenc-price is ONLY for the $AGENC token. Use it ONLY when the user explicitly says "AGENC", "my token", "our token", or "the token".
- "$AGENC price" or "my token price" → "agenc-price --display price"
- "$AGENC market cap" → "agenc-price --display mcap"
- "$AGENC liquidity" → "agenc-price --display liq"
- "everything about AGENC" → "agenc-price --display"

For ANY OTHER crypto (Solana, Bitcoin, Ethereum, etc.) or general topic, use agenc-browse to search the web:
- "Solana price" → agenc-browse https://html.duckduckgo.com/html/?q=solana+price
- "Bitcoin news" → agenc-browse https://html.duckduckgo.com/html/?q=bitcoin+news
- "What is Ethereum" → agenc-browse https://html.duckduckgo.com/html/?q=what+is+ethereum
NEVER use agenc-price for anything other than $AGENC.

Keep "speak" SHORT — 1-2 sentences, under 25 words. Be direct and natural."""

# ============ LOGGING ============
def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

try:
    open(LOG_FILE, "w").close()
except:
    pass

log("Starting AgenC Voice Agent...")
log(f"Model: {GROK_MODEL}")

# ============ AUDIO MIXER SETUP (WM8960 — must run every boot) ============
def setup_audio():
    """Configure WM8960 mic gain, speaker output, and volumes."""
    cmds = [
        "amixer -c 0 cset numid=1 40,40",       # Capture Volume (lowered for VAD)
        "amixer -c 0 cset numid=36 200,200",     # ADC PCM Capture Volume (lowered)
        "amixer -c 0 cset numid=50 on",           # Left Input Mixer Boost
        "amixer -c 0 cset numid=51 on",           # Right Input Mixer Boost
        "amixer -c 0 cset numid=9 2",             # LINPUT1 Boost +20dB (was +29dB)
        "amixer -c 0 cset numid=8 2",             # RINPUT1 Boost +20dB (was +29dB)
        "amixer -c 0 cset numid=52 on",           # Left Output Mixer PCM ON
        "amixer -c 0 cset numid=55 on",           # Right Output Mixer PCM ON
        "amixer -c 0 cset numid=13 120,120",      # Speaker Volume
        "amixer -c 0 cset numid=16 5",             # Speaker AC Boost
        "amixer -c 0 cset numid=15 5",             # Speaker DC Boost
        "amixer -c 0 cset numid=10 235,235",      # Playback Volume
        "amixer -c 0 cset numid=11 120,120",      # Headphone Volume
    ]
    for cmd in cmds:
        subprocess.run(cmd.split(), capture_output=True, timeout=5)
    log("Audio mixer configured")

setup_audio()

# ============ DISPLAY ============
board = WhisPlayBoard()

try:
    FONT_SM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    FONT_MD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
except:
    try:
        FONT_SM = ImageFont.truetype("/usr/share/fonts/ttf/DejaVuSans.ttf", 11)
        FONT_MD = ImageFont.truetype("/usr/share/fonts/ttf/DejaVuSans-Bold.ttf", 13)
    except:
        FONT_SM = ImageFont.load_default()
        FONT_MD = FONT_SM

# ============ STATE ============
task_count = 0
anim_phase = 0.0
blink_state = 0.0
next_blink = time.time() + random.uniform(2, 5)
conversation = []
_bal_cache = {"v": 0.0, "t": 0}

# ============ FACE ============
def ease(t):
    return t * t * (3 - 2 * t)

def draw_rrect(draw, xy, r, fill):
    x1, y1, x2, y2 = xy
    r = min(r, (x2-x1)//2, (y2-y1)//2)
    if r < 1: draw.rectangle(xy, fill=fill); return
    draw.rectangle([x1+r,y1,x2-r,y2], fill=fill)
    draw.rectangle([x1,y1+r,x2,y2-r], fill=fill)
    draw.pieslice([x1,y1,x1+2*r,y1+2*r], 180, 270, fill=fill)
    draw.pieslice([x2-2*r,y1,x2,y1+2*r], 270, 360, fill=fill)
    draw.pieslice([x1,y2-2*r,x1+2*r,y2], 90, 180, fill=fill)
    draw.pieslice([x2-2*r,y2-2*r,x2,y2], 0, 90, fill=fill)

EXPR = {
    "idle":      {"ew":40,"eh":44,"er":14,"sp":72,"ey":-20,"mx":"smile","mw":36,"mc":8,"c":(255,255,255)},
    "listening": {"ew":48,"eh":52,"er":16,"sp":72,"ey":-18,"mx":"open","mw":20,"mh":12,"c":(200,180,255)},
    "thinking":  {"ew":44,"eh":24,"er":10,"sp":64,"ey":-16,"mx":"dots","c":(255,200,100)},
    "speaking":  {"ew":42,"eh":46,"er":14,"sp":72,"ey":-20,"mx":"wave","mw":50,"ma":6,"c":(150,255,180)},
    "executing": {"ew":38,"eh":38,"er":12,"sp":70,"ey":-18,"mx":"flat","mw":26,"c":(100,200,255)},
    "confirmed": {"ew":44,"eh":30,"er":14,"sp":72,"ey":-18,"mx":"smile","mw":44,"mc":14,"c":(100,255,200)},
    "error":     {"ew":38,"eh":28,"er":8,"sp":60,"ey":-14,"mx":"smile","mw":30,"mc":-8,"c":(255,80,80)},
}

def render_face(state, phase, sub=None, wpub="", bal=0.0, tc=0):
    global blink_state, next_blink
    img = Image.new("RGB", (W,H), (0,0,0))
    draw = ImageDraw.Draw(img)
    e = EXPR.get(state, EXPR["idle"])
    col = e["c"]
    cx, cy = W//2, H//2 - 20
    now = time.time()
    if state in ("idle","speaking","confirmed") and now >= next_blink:
        blink_state = 1.0
        next_blink = now + random.uniform(2.5, 5.0)
    if blink_state > 0:
        blink_state = max(0, blink_state - 0.25)
    eh = int(e["eh"] * (1.0 - ease(blink_state)))
    gx = int(math.sin(phase*0.7)*3) if state == "idle" else 0
    gy = int(math.cos(phase*0.9)*2) if state == "idle" else 0
    for side in (-1, 1):
        ex = cx + side * e["sp"]//2 + gx
        ey = cy + e["ey"] + gy
        if eh < 2:
            draw.rectangle([ex-e["ew"]//2, ey-1, ex+e["ew"]//2, ey+1], fill=col)
        else:
            draw_rrect(draw, [ex-e["ew"]//2, ey-eh//2, ex+e["ew"]//2, ey+eh//2], e["er"], col)
    my = cy + 40
    mt = e["mx"]
    if mt == "smile":
        c = e.get("mc", 8)
        if abs(c) < 2:
            draw.line([(cx-e["mw"]//2,my),(cx+e["mw"]//2,my)], fill=col, width=2)
        elif c > 0:
            draw.arc([cx-e["mw"]//2,my-c,cx+e["mw"]//2,my+c], 0, 180, fill=col, width=2)
        else:
            c = abs(c)
            draw.arc([cx-e["mw"]//2,my-c,cx+e["mw"]//2,my+c], 180, 360, fill=col, width=2)
    elif mt == "open":
        draw_rrect(draw,[cx-e["mw"]//2,my-e.get("mh",12)//2,cx+e["mw"]//2,my+e.get("mh",12)//2],
                   min(e["mw"],e.get("mh",12))//2, col)
    elif mt == "wave":
        pts = []
        hw = e["mw"]//2
        for i in range(-hw, hw+1, 2):
            t = i/hw
            y = int(math.sin(phase+t*8)*e.get("ma",6)*(1-t*t*0.3))
            pts.append((cx+i, my+y))
        if len(pts)>1: draw.line(pts, fill=col, width=3)
    elif mt == "dots":
        for i in range(3):
            b = max(0, math.sin(phase*4-i*0.4))*8
            dx = (i-1)*16
            draw.ellipse([cx+dx-4,my-4-int(b),cx+dx+4,my+4-int(b)], fill=col)
    elif mt == "flat":
        draw.line([(cx-15,my),(cx+15,my)], fill=col, width=2)
    if sub:
        bb = draw.textbbox((0,0), sub, font=FONT_MD)
        tw = bb[2]-bb[0]
        x = max(4, (W-tw)//2)
        draw.text((x, H-52), sub, fill=tuple(max(0,c//3) for c in col), font=FONT_MD)
    draw.line([(15,H-34),(W-15,H-34)], fill=(25,25,30), width=1)
    if wpub:
        draw.text((8,H-28), wpub[:18]+"..", fill=(50,50,55), font=FONT_SM)
    info = f"{bal:.3f} SOL  T:{tc}"
    bb = draw.textbbox((0,0), info, font=FONT_SM)
    draw.text((W-8-(bb[2]-bb[0]), H-28), info, fill=(50,50,55), font=FONT_SM)
    return img

def show_face(state, sub=None, wpub="", bal=0.0, tc=0):
    global anim_phase
    img = render_face(state, anim_phase, sub, wpub, bal, tc)
    px = img.load()
    buf = bytearray(W*H*2)
    idx = 0
    for y in range(H):
        for x in range(W):
            r,g,b = px[x,y]
            v = ((r&0xF8)<<8)|((g&0xFC)<<3)|(b>>3)
            buf[idx] = (v>>8)&0xFF; buf[idx+1] = v&0xFF; idx += 2
    board.set_backlight(100)
    board.draw_image(0, 0, W, H, buf)
    anim_phase += 0.2

def animate_face(state, dur, sub=None, wpub="", bal=0.0, tc=0):
    t0 = time.time()
    while time.time()-t0 < dur:
        show_face(state, sub, wpub, bal, tc)
        time.sleep(0.07)

def set_led(state):
    c = EXPR.get(state, EXPR["idle"])["c"]
    board.set_rgb(c[0]//3, c[1]//3, c[2]//3)

# ============ WALLET ============
def load_wallet():
    try:
        from solders.keypair import Keypair
    except ImportError:
        log("WARNING: solders not installed, wallet disabled")
        return None
    os.makedirs(os.path.dirname(WALLET_PATH), exist_ok=True)
    if os.path.exists(WALLET_PATH):
        with open(WALLET_PATH) as f: secret = json.load(f)
        kp = Keypair.from_bytes(bytes(secret))
    else:
        kp = Keypair()
        with open(WALLET_PATH, "w") as f: json.dump(list(bytes(kp)), f)
        os.chmod(WALLET_PATH, 0o600)
    log(f"Wallet: {kp.pubkey()}")
    return kp

def sol_rpc(method, params=None):
    """Call Solana JSON-RPC via urllib (no solana-py needed)."""
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(DEVNET_RPC, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def get_balance(w):
    if w is None: return 0.0
    try:
        r = sol_rpc("getBalance", [str(w.pubkey())])
        return r["result"]["value"] / 1e9
    except: return 0.0

def request_airdrop(w, amount=1.0):
    """Request devnet airdrop."""
    if w is None: return None
    try:
        r = sol_rpc("requestAirdrop", [str(w.pubkey()), int(amount * 1e9)])
        return r.get("result")
    except Exception as e:
        log(f"Airdrop error: {e}")
        return None

def get_balance_cached(w):
    if w is None: return 0.0
    now = time.time()
    if now - _bal_cache["t"] > 30:
        _bal_cache["v"] = get_balance(w)
        _bal_cache["t"] = now
    return _bal_cache["v"]

def write_memo(w, memo):
    from solana.rpc.api import Client
    from solders.transaction import Transaction
    from solders.message import Message
    from solders.instruction import Instruction, AccountMeta
    from solders.pubkey import Pubkey
    c = Client(DEVNET_RPC)
    mp = Pubkey.from_string(MEMO_PROGRAM_ID)
    ix = Instruction(mp, memo.encode("utf-8")[:566],
        [AccountMeta(w.pubkey(), is_signer=True, is_writable=True)])
    bh = c.get_latest_blockhash().value.blockhash
    msg = Message.new_with_blockhash([ix], w.pubkey(), bh)
    tx = Transaction.new_unsigned(msg)
    tx.sign([w], bh)
    return str(c.send_transaction(tx).value)

# ============ AUDIO ============
MAX_RECORD_SECONDS = 3

def check_soundcard():
    """Check if WM8960 is available. Reload driver if not."""
    r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5)
    if "no soundcards" in (r.stdout + r.stderr).lower():
        log("No soundcard! Reloading WM8960 driver...")
        subprocess.run("modprobe -r snd_soc_wm8960; sleep 1; modprobe snd_soc_wm8960; sleep 2", shell=True, timeout=10)
        setup_audio()
        r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5)
        if "no soundcards" in (r.stdout + r.stderr).lower():
            log("Soundcard still not found after reload")
            return False
        log("Soundcard recovered!")
    return True

def record_audio():
    """Record fixed duration audio. Simple and reliable."""
    wav = "/tmp/agenc_input.wav"
    if not check_soundcard():
        return None
    try:
        log("Recording...")
        subprocess.run(
            ["arecord", "-D", AUDIO_DEV, "-f", "S16_LE", "-r", "24000", "-c", "1",
             "-d", str(MAX_RECORD_SECONDS), "-q", wav],
            timeout=MAX_RECORD_SECONDS + 3, capture_output=True)
        if os.path.exists(wav) and os.path.getsize(wav) > 5000:
            dur = os.path.getsize(wav) / (24000 * 2)
            log(f"Recorded {dur:.1f}s")
            return wav
        log("Too short")
        return None
    except Exception as e:
        log(f"Record error: {e}")
        return None

# ============ VAD (Voice Activity Detection) for always-listening mode ============
VAD_CHUNK_SAMPLES = 12000  # 0.5s at 24kHz (use --samples for sub-second recording)
VAD_THRESHOLD = 800        # RMS threshold — ambient ~200 with current gain, speech ~1000+
VAD_RECORD_SEC = 3         # Once speech detected, record this many additional seconds
VAD_COOLDOWN = 5.0         # Seconds to skip VAD after speaking (avoid catching own TTS echo)
_last_speak_time = 0.0     # Timestamp of last TTS playback end

def compute_rms(pcm_data):
    """Compute RMS of 16-bit PCM data."""
    if len(pcm_data) < 2:
        return 0
    n_samples = len(pcm_data) // 2
    total = 0
    for i in range(n_samples):
        sample = struct.unpack_from('<h', pcm_data, i * 2)[0]
        total += sample * sample
    return math.sqrt(total / n_samples) if n_samples > 0 else 0

def record_audio_vad():
    """Always-listening: record short chunks, detect speech by volume, capture full utterance."""
    global _last_speak_time
    # Skip if we just finished speaking (avoid catching own TTS output)
    if time.time() - _last_speak_time < VAD_COOLDOWN:
        time.sleep(0.2)
        return None
    if not check_soundcard():
        return None

    chunk_file = "/tmp/agenc_vad_chunk.wav"

    # Record a short chunk (0.5s) to check for speech
    try:
        subprocess.run(
            ["arecord", "-D", AUDIO_DEV, "-f", "S16_LE", "-r", "24000", "-c", "1",
             "--samples", str(VAD_CHUNK_SAMPLES), "-q", chunk_file],
            timeout=3, capture_output=True)
    except Exception as e:
        log(f"VAD chunk error: {e}")
        return None

    if not os.path.exists(chunk_file) or os.path.getsize(chunk_file) < 100:
        return None

    # Read the chunk and compute RMS
    with open(chunk_file, "rb") as f:
        raw = f.read()
    pcm = raw[44:]  # skip WAV header
    rms = compute_rms(pcm)

    if rms < VAD_THRESHOLD:
        return None  # silence — keep listening

    # Speech detected! Record the full utterance
    log(f"Voice detected (RMS={rms:.0f}), recording {VAD_RECORD_SEC}s...")
    wav = "/tmp/agenc_input.wav"
    try:
        subprocess.run(
            ["arecord", "-D", AUDIO_DEV, "-f", "S16_LE", "-r", "24000", "-c", "1",
             "-d", str(VAD_RECORD_SEC), "-q", wav],
            timeout=VAD_RECORD_SEC + 3, capture_output=True)
        if os.path.exists(wav) and os.path.getsize(wav) > 5000:
            dur = os.path.getsize(wav) / (24000 * 2)
            log(f"Captured {dur:.1f}s utterance")
            return wav
        log("Capture too short")
        return None
    except Exception as e:
        log(f"VAD record error: {e}")
        return None

# ============ STT via xAI Realtime WebSocket ============
async def xai_stt(wav_path):
    """Send audio to xAI Realtime, get back transcription only."""
    try:
        with open(wav_path, "rb") as f:
            raw = f.read()
        pcm = raw[44:]  # skip WAV header
        if len(pcm) < 4800:
            log("Audio too short")
            return None

        headers = {"Authorization": f"Bearer {XAI_API_KEY}"}
        async with websockets.connect(WS_URL,
            extra_headers=headers,
            ping_interval=10, close_timeout=2) as ws:

            # Drain init messages (tight timeouts)
            for _ in range(3):
                try:
                    m = await asyncio.wait_for(ws.recv(), timeout=1)
                except asyncio.TimeoutError:
                    break

            # Configure for transcription
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "turn_detection": None,
                    "input_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "grok-2-public"},
                    "instructions": "Transcribe the user's speech exactly. The user speaks English, Spanish, or German about crypto, Solana, AI agents. Respond: {\"transcription\": \"what they said\"}"
                }
            }))
            try:
                await asyncio.wait_for(ws.recv(), timeout=2)
            except asyncio.TimeoutError:
                pass

            # Send ALL audio at once (faster than chunking)
            b64audio = base64.b64encode(pcm).decode()
            await ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": b64audio
            }))

            await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            await ws.send(json.dumps({
                "type": "response.create",
                "response": {"modalities": ["text"]}
            }))

            # Collect transcription (tight timeout)
            input_transcript = None
            text_parts = []

            for _ in range(15):
                try:
                    m = await asyncio.wait_for(ws.recv(), timeout=5)
                    d = json.loads(m)
                    mt = d.get("type", "")

                    if mt == "conversation.item.input_audio_transcription.completed":
                        input_transcript = d.get("transcript", "")
                        log(f"STT: '{input_transcript}'")
                    elif mt == "response.text.delta":
                        text_parts.append(d.get("delta", ""))
                    elif mt == "response.done":
                        break
                    elif mt == "error":
                        log(f"STT error: {json.dumps(d)[:300]}")
                        break
                except asyncio.TimeoutError:
                    log("STT timeout")
                    break

            # Prefer input transcription, fallback to response text
            if input_transcript:
                return input_transcript

            # Try to extract from response text
            full_text = "".join(text_parts)
            if full_text:
                try:
                    d = json.loads(full_text)
                    return d.get("transcription", full_text)
                except:
                    return full_text

            return None

    except Exception as e:
        log(f"STT error: {e}")
        return None

def transcribe(wav_path):
    """Synchronous wrapper for STT."""
    return asyncio.run(xai_stt(wav_path))

# ============ GROK 4.20 CHAT API (via urllib — no requests needed) ============
def ask_grok(messages):
    """Call Grok 4.20 chat API using urllib (no external deps)."""
    payload = json.dumps({
        "model": GROK_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages[-10:],
        "max_tokens": 150,
        "temperature": 0.2
    }).encode("utf-8")

    req = urllib.request.Request(GROK_API_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {XAI_API_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "AgenC-One/1.0")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"): text = text[:-3]
            text = text.strip()
        log(f"Grok response: {text[:200]}")
        return parse_json_response(text)
    except Exception as e:
        log(f"Grok API error: {e}")
        return None

def parse_json_response(text):
    """Parse JSON from Grok response, handling quirks."""
    if not text:
        return None
    text = text.strip()

    # Try standard JSON
    try:
        return json.loads(text)
    except:
        pass

    # Find JSON-like pattern
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        blob = m.group(0)
        try:
            return json.loads(blob)
        except:
            pass
        # Extract key-value pairs manually
        result = {}
        for key in ("cmd", "speak", "voice"):
            pat = key + r'\s*:\s*'
            km = re.search(pat, blob)
            if km:
                rest = blob[km.end():]
                if rest.startswith('"'):
                    em = re.search(r'"((?:[^"\\]|\\.)*)"', rest)
                    if em: result[key] = em.group(1)
                elif rest.startswith("'"):
                    em = re.search(r"'((?:[^'\\]|\\.)*)'", rest)
                    if em: result[key] = em.group(1)
                else:
                    em = re.search(r'^(.*?)(?:,\s*(?:cmd|speak|voice)\s*:|[}])', rest, re.DOTALL)
                    if em: result[key] = em.group(1).strip().strip('"').strip("'")
                    else: result[key] = rest.strip().rstrip('}').strip().strip('"').strip("'")
        if result:
            return result

    # Fallback: treat as speak text
    clean = text.strip('{}').strip()
    if clean:
        return {"speak": clean}
    return None

# ============ xAI TTS API (new dedicated endpoint) ============
def mute_mic(mute=True):
    """Mute/unmute capture to prevent speaker feedback into mic."""
    val = "off" if mute else "on"
    subprocess.run(["amixer", "-c", "0", "cset", "numid=3", val+","+val],
                   capture_output=True, timeout=3)

def speak(text):
    """Convert text to speech using xAI TTS API and play it."""
    voice = current_voice if current_voice in TTS_VOICES else "ara"
    log(f"TTS ({voice}): '{text[:60]}...'")

    payload = json.dumps({
        "text": text[:4000],
        "voice_id": voice,
        "output_format": {
            "codec": "wav",
            "sample_rate": 24000
        }
    }).encode("utf-8")

    req = urllib.request.Request(TTS_API_URL, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {XAI_API_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "AgenC-One/1.0")

    wav_path = "/tmp/agenc_response.wav"
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        with open(wav_path, "wb") as f:
            f.write(audio)
        dur = len(audio) / (24000 * 2)
        log(f"TTS audio: {dur:.1f}s ({len(audio)} bytes)")
        mute_mic(True)
        subprocess.run(["aplay", "-D", AUDIO_DEV, wav_path], timeout=60, capture_output=True)
        mute_mic(False)
        _update_speak_time()
    except Exception as e:
        mute_mic(False)
        _update_speak_time()
        log(f"TTS error: {e}")

def _update_speak_time():
    global _last_speak_time
    _last_speak_time = time.time()

# ============ COMMAND EXECUTION ============
DISPLAY_CMDS = ("agenc-qr", "agenc-price --display", "agenc-display")
QR_CMDS = ("agenc-qr",)  # These stay on screen until button pressed

def cmd_writes_display(cmd):
    return any(dc in cmd for dc in DISPLAY_CMDS)

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = r.stdout.strip()
        if r.stderr.strip(): out += ("\n" if out else "") + r.stderr.strip()
        return out if out else "(no output)"
    except subprocess.TimeoutExpired: return "(timed out)"
    except Exception as e: return f"(error: {e})"

def unwrap_nested(parsed):
    """Unwrap nested responses like {"Action": {"cmd":..., "speak":...}}"""
    if not parsed:
        return parsed
    # If top-level has no cmd/speak but has a nested dict with them, unwrap
    if "cmd" not in parsed and "speak" not in parsed:
        for key in parsed:
            if isinstance(parsed[key], dict) and ("cmd" in parsed[key] or "speak" in parsed[key]):
                return parsed[key]
    return parsed

def execute_and_followup(parsed, conversation, pub, bal):
    """Execute command and get follow-up from Grok to summarize output."""
    global current_voice, task_count

    parsed = unwrap_nested(parsed)
    if not parsed:
        return "I didn't catch that.", False

    # Handle voice change
    if "voice" in parsed:
        v = parsed["voice"].lower().strip()
        if v == "random" or v not in TTS_VOICES:
            # Pick a random voice different from current
            others = [x for x in TTS_VOICES if x != current_voice]
            v = random.choice(others)
        current_voice = v
        log(f"Voice -> {current_voice}")

    speak_text = parsed.get("speak", "")

    # No command — just speak
    if "cmd" not in parsed or not parsed["cmd"].strip():
        return speak_text or "Done.", False

    cmd = parsed["cmd"].strip()
    log(f"CMD: {cmd}")
    set_led("executing")
    show_face("executing", "Running...", pub, bal, task_count)
    output = run_cmd(cmd)
    log(f"Output: {output[:200]}")
    wrote = cmd_writes_display(cmd)

    # For display commands with a speak already, skip follow-up (speed optimization)
    if wrote and speak_text:
        # Try to enrich speak with JSON output data
        try:
            data = json.loads(output)
            if "price" in (speak_text.lower() + cmd.lower()) and "price" in data:
                speak_text = f"AGENC is at {data['price']}"
            elif "cap" in (speak_text.lower() + cmd.lower()) and "mcap" in data:
                speak_text = f"Market cap is {data['mcap']}"
        except:
            pass
        return speak_text, wrote

    # Add to conversation for follow-up
    conversation.append({"role": "assistant", "content": json.dumps(parsed)})
    conversation.append({"role": "user", "content": f"Command output:\n{output[:1000]}\nRespond with SHORT speak ONLY about what was asked."})

    # Get follow-up from Grok 4.20 to summarize the output
    set_led("thinking")
    followup = ask_grok(conversation)
    if followup:
        followup = unwrap_nested(followup)
        if "cmd" in followup and followup["cmd"].strip():
            return execute_and_followup(followup, conversation, pub, bal)
        speak_text = followup.get("speak", speak_text)

    return speak_text or "Done.", wrote

# ============ DISPLAY HELPERS ============
def show_text_on_display(text):
    try:
        subprocess.run(["agenc-display", "text", text[:200], "--color", "green", "--bg", "black"],
            timeout=5, capture_output=True)
    except: pass

def safe_kill(name):
    try: subprocess.run(["killall", name], capture_output=True, timeout=3)
    except: pass

# ============ MAIN CYCLE ============
ALWAYS_LISTEN = True   # True = always-listening (no button), False = button mode
SLEEP_TIMEOUT = 600
DISPLAY_DURATION = 8

wallet = None
task_count = 0

def get_info():
    pub = str(wallet.pubkey()) if wallet else "none"
    bal = get_balance_cached(wallet) if wallet else 0.0
    return pub, bal

def do_one_cycle_with_audio(wav):
    """STT → Grok 4.20 → Execute → TTS. Takes pre-recorded audio (for VAD mode)."""
    global conversation, task_count, current_voice
    pub, bal = get_info()
    return _process_audio(wav, pub, bal)

def do_one_cycle():
    """Record → STT → Grok 4.20 → Execute → TTS. Clean pipeline."""
    global conversation, task_count, current_voice
    pub, bal = get_info()

    # 1. RECORD
    log("Listening...")
    set_led("listening")
    show_face("listening", "Listening...", pub, bal, task_count)
    wav = record_audio()
    if not wav:
        time.sleep(2)
        return False
    return _process_audio(wav, pub, bal)

def _process_audio(wav, pub, bal):
    """Core pipeline: STT → Grok → Execute → TTS."""
    global conversation, task_count, current_voice

    # 2. STT (xAI Realtime WebSocket → transcription)
    log("Transcribing...")
    set_led("thinking")
    show_face("thinking", "Hearing...", pub, bal, task_count)
    user_text = transcribe(wav)
    if not user_text:
        log("STT returned nothing")
        set_led("error")
        animate_face("error", 1.5, "Didn't hear", pub, bal, task_count)
        return False
    log(f"User said: '{user_text}'")
    conversation.append({"role": "user", "content": user_text})

    # 3. GROK 4.20
    log("Thinking with Grok 4.20...")
    set_led("thinking")
    show_face("thinking", "Thinking...", pub, bal, task_count)
    parsed = unwrap_nested(ask_grok(conversation))
    if not parsed:
        log("Grok returned nothing")
        set_led("error")
        animate_face("error", 1.5, "No response", pub, bal, task_count)
        return False
    log(f"Parsed: {parsed}")

    # 4. EXECUTE COMMANDS if needed, get follow-up
    speak_text, wrote_display = execute_and_followup(parsed, conversation, pub, bal)
    if not speak_text:
        speak_text = parsed.get("speak", "Done.")
    log(f"Answer: {speak_text}")
    conversation.append({"role": "assistant", "content": json.dumps(parsed)})

    # 5. ON-CHAIN MEMO (only for tool commands that actually ran)
    if "cmd" in (parsed or {}) and parsed.get("cmd", "").strip() and wallet:
        set_led("confirmed")
        try:
            memo = json.dumps({"p":"agenc-v1","agent":"AgenC-One","act":"task_complete",
                "task":(user_text or "voice_cmd")[:100],"t":int(time.time())}, separators=(",",":"))
            sig = write_memo(wallet, memo)
            task_count += 1
            log(f"TX: {sig}")
        except Exception as e:
            log(f"TX error: {e}")

    # 6. SPEAK + SHOW ON DISPLAY (simultaneously — display stays during and after speech)
    log("Speaking...")
    set_led("speaking")
    if not wrote_display:
        show_text_on_display(speak_text)
    done = [False]
    def do_speak(): speak(speak_text); done[0] = True
    t = threading.Thread(target=do_speak, daemon=True); t.start()
    while not done[0]:
        time.sleep(0.1)
    t.join()

    # QR commands: keep on screen until button pressed
    cmd_str = (parsed or {}).get("cmd", "")
    if any(qc in cmd_str for qc in QR_CMDS):
        log("QR on screen — waiting for button press...")
        set_led("confirmed")
        while not board.button_pressed():
            time.sleep(0.1)
        # Wait for release
        while board.button_pressed():
            time.sleep(0.05)
    else:
        # Keep result on screen for at least 5 seconds after speech finishes
        time.sleep(5)
    _bal_cache["t"] = 0  # refresh balance next time
    return True

# ============ BOOT ============
log("Loading wallet...")
wallet = load_wallet()
if wallet:
    bal = get_balance(wallet)
    if bal < 0.01:
        log("Low balance, requesting airdrop...")
        sig = request_airdrop(wallet, 1.0)
        if sig:
            time.sleep(2)
            bal = get_balance(wallet)
            log(f"Airdrop OK: {bal} SOL")
else:
    bal = 0.0
_bal_cache["v"] = bal; _bal_cache["t"] = time.time()
pub = str(wallet.pubkey()) if wallet else "no-wallet"
log(f"Balance: {bal} SOL")
log(f"Voice: {current_voice}")
log(f"Model: {GROK_MODEL}")
log("=== Ready ===")

set_led("speaking")
show_face("speaking", "Booting...", pub, bal, task_count)
if ALWAYS_LISTEN:
    speak("AgenC One online. Powered by Grok 4.20. I'm listening.")
else:
    speak("AgenC One online. Powered by Grok 4.20. Press button to speak.")
time.sleep(0.3)

set_led("idle")
idle_msg = "Listening..." if ALWAYS_LISTEN else "Press button"
show_face("idle", idle_msg, pub, bal, task_count)
last_act = time.time()
last_idle_draw = time.time()
sleeping = False
led_phase = 0.0
log(f"=== {'Always-listening' if ALWAYS_LISTEN else 'Button'} mode ===")

def wait_for_button_release():
    """Wait until button is released to avoid double-trigger."""
    for _ in range(50):
        if not board.button_pressed(): return
        time.sleep(0.05)

while True:
    if ALWAYS_LISTEN:
        # === ALWAYS-LISTENING MODE (no button needed) ===
        if sleeping:
            # Wake on button press only
            if board.button_pressed():
                log("=== WAKE ===")
                sleeping = False
                pub, bal = get_info()
                set_led("speaking")
                speak("I'm back. I'm listening.")
                wait_for_button_release()
                last_act = time.time()
            else:
                time.sleep(0.3)
                continue

        # Try to detect speech via VAD
        wav = record_audio_vad()
        if wav:
            last_act = time.time()
            pub, bal = get_info()
            set_led("listening")
            show_face("listening", "Heard you...", pub, bal, task_count)
            # Feed detected audio directly into the pipeline (skip re-recording)
            do_one_cycle_with_audio(wav)
            pub, bal = get_info()
            set_led("idle")
            show_face("idle", "Listening...", pub, bal, task_count)
            last_idle_draw = time.time()
            time.sleep(0.5)  # brief pause before listening again
        else:
            # No speech — idle animations
            if time.time() - last_act > SLEEP_TIMEOUT:
                log("=== SLEEP ===")
                safe_kill("arecord"); safe_kill("aplay")
                board.set_backlight(0); board.set_rgb(0,0,0); board.fill_screen(0x0000)
                sleeping = True
            else:
                led_phase += 0.05
                brightness = int(40 + 30 * math.sin(led_phase))
                board.set_rgb(0, brightness, brightness)
                if time.time() - last_idle_draw > 5:
                    pub, bal = get_info()
                    show_face("idle", "Listening...", pub, bal, task_count)
                    last_idle_draw = time.time()
    else:
        # === BUTTON MODE (original) ===
        if board.button_pressed():
            if sleeping:
                log("=== WAKE ===")
                sleeping = False
                pub, bal = get_info()
                set_led("speaking")
                speak("I'm back.")
            last_act = time.time()
            pub, bal = get_info()
            set_led("listening")
            show_face("listening", "Listening...", pub, bal, task_count)
            do_one_cycle()
            wait_for_button_release()
            pub, bal = get_info()
            set_led("idle")
            show_face("idle", "Press button", pub, bal, task_count)
            last_idle_draw = time.time()
            time.sleep(0.3)
        elif not sleeping:
            if time.time() - last_act > SLEEP_TIMEOUT:
                log("=== SLEEP ===")
                safe_kill("arecord"); safe_kill("aplay")
                board.set_backlight(0); board.set_rgb(0,0,0); board.fill_screen(0x0000)
                sleeping = True
            else:
                led_phase += 0.05
                brightness = int(40 + 30 * math.sin(led_phase))
                board.set_rgb(0, brightness, brightness)
                if time.time() - last_idle_draw > 5:
                    pub, bal = get_info()
                    show_face("idle", "Press button", pub, bal, task_count)
                    last_idle_draw = time.time()
                time.sleep(0.15)
        else:
            time.sleep(0.3)
