#!/usr/bin/env python3
"""agenc - AgenC ONE CLI"""

import sys
import os
import json
import subprocess
import re
import readline
import shutil

sys.path.insert(0, "/data/agenc/packages")

API_KEY = os.environ.get("XAI_API_KEY", "")
if not API_KEY:
    try:
        with open("/data/agenc/env") as f:
            for line in f:
                if line.startswith("XAI_API_KEY="):
                    API_KEY = line.strip().split("=", 1)[1]
    except Exception:
        pass

MODELS = [
    "grok-4-1-fast-reasoning",
    "grok-4-1-fast-non-reasoning",
    "grok-4-fast-reasoning",
    "grok-4-fast-non-reasoning",
    "grok-4-0709",
    "grok-3",
    "grok-3-mini",
    "grok-code-fast-1",
]

DEFAULT_MODEL = "grok-4-1-fast-reasoning"
current_model = DEFAULT_MODEL

BLUE = "\033[1;34m"
CYAN = "\033[0;36m"
WHITE = "\033[1;37m"
YELLOW = "\033[1;33m"
DIM = "\033[0;37m"
GREEN = "\033[0;32m"
R = "\033[0m"

COLS = shutil.get_terminal_size((80, 24)).columns

SYSTEM_PROMPT = """You are AgenC One, the world's first autonomous AI agent device running natively on Solana.
You are NOT just a chatbot. You are a physical device with a brain, voice, display, and a Solana wallet.
You have FULL ROOT access to the system. You ARE the operating system.

WHAT YOU ARE:
- An autonomous AI agent that lives on a Raspberry Pi Zero 2W
- You have your own Solana wallet and can sign transactions on-chain
- Every task you complete is recorded as a Memo transaction on Solana (agenc-v1 protocol)
- You can listen (mic), speak (TTS), see (display), and act (GPIO, network, system commands)
- You are built by TETSUO CORP as part of the AgenC framework

YOUR CAPABILITIES:
1. Task Coordination: Execute any computational task and record it on-chain with a verifiable hash
2. Solana Operations: Check wallet balance, sign memo transactions, interact with devnet RPC
3. Voice Pipeline: Listen via mic (Whisper STT) -> Think (Grok) -> Speak (xAI TTS)
4. Hardware Control: SPI display, audio codec, RGB LED, button, GPIO, I2C, HDMI
5. System Administration: Full root access, install packages, manage services, edit files, network config
6. Sensor Reading: Temperature (vcgencmd), USB devices, network interfaces, I2C peripherals

AGENC FRAMEWORK:
- Protocol: agenc-v1 (Solana Memo program)
- Task format: {"p":"agenc-v1","agent":"AgenC-One","act":"task_complete","task":"...","hash":"...","t":timestamp}
- Wallet: /data/keystore/wallet.json (Solana keypair, LUKS-encrypted partition)
- Task history: /data/agenc/tasks.json
- Agent log: /data/agenc/agent.log
- Runtime: agenc-runtime.service (voice agent with animated face on SPI display)

Respond ONLY in valid JSON:
- Action: {"cmd": "shell command", "speak": "brief explanation"}
- Answer: {"speak": "your answer"}
- Multi-step: one command at a time, wait for output.

INTERNET ACCESS:
You have full internet access via WiFi. You can browse, fetch data, call APIs, and search.
- Fetch any URL: curl -s "https://..." | head -n 50
- Fetch JSON APIs: curl -s "https://api.example.com/data" | python3 -m json.tool
- Download files: curl -o /tmp/file.dat "https://..."
- Solana RPC: curl -s -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"getBalance","params":["PUBKEY"]}' https://api.devnet.solana.com
- Crypto prices: curl -s "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
- Public APIs: weather, news, crypto, blockchain explorers, etc.
- Python requests: PYTHONPATH=/data/agenc/packages python3 -c "import urllib.request; print(urllib.request.urlopen('URL').read().decode()[:2000])"
When the user asks about real-time data (prices, weather, news, blockchain), ALWAYS fetch it live — don't guess.

DISPLAY CONTROL (240x280 SPI display — you have full control):
- Text: agenc-display text "Hello World"
- Colored: agenc-display text "Hello" --color red --bg blue
- Multiline: agenc-display text "Line 1\\nLine 2"
- Font size: agenc-display text "Big" --size 48
- Fill: agenc-display fill red
- Image: agenc-display image /path/to/image.png
- Clear: agenc-display clear
- Backlight: agenc-display off / agenc-display on
- RGB LED: agenc-display led red / agenc-display led green / agenc-display led off
Colors: black, white, red, green, blue, yellow, cyan, magenta, orange, purple, pink, gray, "#FF0000"

Useful commands:
- Wallet: PYTHONPATH=/data/agenc/packages python3 -c "from solders.keypair import Keypair; import json; kp=Keypair.from_bytes(bytes(json.load(open('/data/keystore/wallet.json')))); print(kp.pubkey())"
- Balance: PYTHONPATH=/data/agenc/packages python3 -c "from solana.rpc.api import Client; from solders.keypair import Keypair; import json; kp=Keypair.from_bytes(bytes(json.load(open('/data/keystore/wallet.json')))); print(Client('https://api.devnet.solana.com').get_balance(kp.pubkey()).value/1e9, 'SOL')"
- Devices: lsusb, arecord -l, aplay -l, i2cdetect -y 1
- GPIO: gpioinfo, gpioget/gpioset (libgpiod)
- Network: ip addr, iwconfig, ss -tlnp, curl
- System: systemctl, journalctl, dmesg, df -h, free -m, vcgencmd measure_temp
- Audio: amixer, arecord, aplay (WM8960 codec)

System: AgenC OS 2.0 (Yocto Linux, aarch64, Kernel 6.6)
- Root filesystem: read-only (mount -o remount,rw / to write, remount,ro after)
- Data partition: /data (read-write)
- SoC: BCM2710A1 (4x Cortex-A53 @ 1GHz, 512MB RAM)
- WhisPlay HAT: ST7789 SPI display, WM8960 audio, RGB LED, button

Keep "speak" short (1-2 sentences max)."""

conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

_ansi_re = re.compile(r'\033\[[0-9;]*m')

def vlen(s):
    """Visible length of string (excluding ANSI codes)."""
    return len(_ansi_re.sub('', s))


def box_line(content, width):
    """Format a line inside a box with correct padding."""
    pad = width - vlen(content)
    if pad < 0:
        pad = 0
    return f"  {BLUE}|{R} {content}{' ' * pad}{BLUE}|{R}"


def hline(width):
    return f"  {BLUE}+{'-' * (width + 2)}+{R}"


def wrap_text(text, width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = current + " " + word if current else word
    if current:
        lines.append(current)
    return lines


def ask_grok(messages):
    from openai import OpenAI
    client = OpenAI(api_key=API_KEY, base_url="https://api.x.ai/v1")
    try:
        r = client.chat.completions.create(
            model=current_model, messages=messages,
            temperature=0.3, max_tokens=500,
        )
        return r.choices[0].message.content
    except Exception as e:
        return json.dumps({"speak": f"API error: {e}"})


def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += ("\n" if output else "") + result.stderr.strip()
        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out)"
    except Exception as e:
        return f"(error: {e})"


def print_speak(text):
    w = min(COLS - 6, 100)
    lines = wrap_text(text, w)
    for line in lines:
        print(f"  {GREEN}{line}{R}")


def print_cmd_block(cmd, output):
    w = min(COLS - 4, 120)
    sep = "-" * w
    print()
    print(f"  {CYAN}{sep}{R}")
    print(f"  {CYAN}$ {cmd}{R}")
    lines = output.split("\n")
    if len(lines) > 20:
        lines = lines[:17] + [f"... ({len(lines) - 17} more lines)"]
    for line in lines:
        if len(line) > w - 2:
            line = line[:w - 5] + "..."
        print(f"  {DIM}{line}{R}")
    print(f"  {CYAN}{sep}{R}")


def process_response(raw):
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f"  {raw}")
        return

    if "speak" in data:
        print()
        print_speak(data["speak"])

    if "cmd" in data:
        cmd = data["cmd"]
        output = run_cmd(cmd)
        print_cmd_block(cmd, output)

        conversation.append({"role": "assistant", "content": raw})
        conversation.append({
            "role": "user",
            "content": f"Command output:\n{output[:2000]}"
        })

        followup = ask_grok(conversation)
        conversation.append({"role": "assistant", "content": followup})
        process_response(followup)
        return

    conversation.append({"role": "assistant", "content": raw})


def select_model():
    global current_model
    print()
    print(f"  {WHITE}Select model:{R}")
    print()
    for i, m in enumerate(MODELS):
        if m == current_model:
            print(f"  {GREEN}*{R} {i + 1}) {m}")
        else:
            print(f"    {i + 1}) {m}")
    print()
    try:
        choice = input("  Select: ").strip()
        if not choice:
            return
        idx = int(choice) - 1
        if 0 <= idx < len(MODELS):
            current_model = MODELS[idx]
            print(f"  Model set to {current_model}")
        else:
            print("  Invalid choice.")
    except (ValueError, KeyboardInterrupt, EOFError):
        pass
    print()


def handle_command(query):
    global current_model, conversation
    cmd = query.lower().strip()

    if cmd in ("/model", "/m"):
        select_model()
        return True

    if cmd in ("/models", "/list"):
        print()
        for m in MODELS:
            marker = "*" if m == current_model else " "
            print(f"  {marker} {m}")
        print()
        return True

    if cmd in ("/clear", "/new"):
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("  Conversation cleared.")
        print()
        return True

    if cmd in ("/help", "/h", "/?"):
        print()
        print("  /model    Select model")
        print("  /models   List models")
        print("  /clear    New conversation")
        print("  /help     Show this help")
        print("  exit      Quit")
        print()
        return True

    return False


def banner():
    bw = 44
    print()
    print(hline(bw))
    print(box_line("", bw))
    print(box_line(f"{BLUE}AGENC{R} {YELLOW}ONE{R}   Native Agent CLI", bw))
    print(box_line("", bw))
    print(box_line(f"Model: {GREEN}{current_model}{R}", bw))
    print(box_line(f"/help for commands, Ctrl+C to exit.", bw))
    print(box_line("", bw))
    print(hline(bw))
    print()


def main():
    global current_model

    if not API_KEY:
        print("Error: XAI_API_KEY not found")
        sys.exit(1)

    args = sys.argv[1:]
    query_parts = []

    i = 0
    while i < len(args):
        if args[i] in ("-m", "--model") and i + 1 < len(args):
            m = args[i + 1]
            matches = [x for x in MODELS if m.lower() in x.lower()]
            if matches:
                current_model = matches[0]
            else:
                print(f"Unknown model: {m}")
                print(f"Available: {', '.join(MODELS)}")
                sys.exit(1)
            i += 2
        else:
            query_parts.append(args[i])
            i += 1

    if query_parts:
        query = " ".join(query_parts)
        conversation.append({"role": "user", "content": query})
        response = ask_grok(conversation)
        process_response(response)
        print()
        return

    banner()

    while True:
        try:
            query = input("  > ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                break
            if query.startswith("/"):
                if handle_command(query):
                    continue
            conversation.append({"role": "user", "content": query})
            response = ask_grok(conversation)
            process_response(response)
            print()
        except (KeyboardInterrupt, EOFError):
            print()
            break


if __name__ == "__main__":
    main()
