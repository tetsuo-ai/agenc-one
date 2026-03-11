# AgenC OS — Runtime Integration Master Plan

> This document is the single source of truth for integrating the @agenc/runtime TypeScript framework
> natively into AgenC OS (custom Yocto Linux for Raspberry Pi Zero 2W).
> It contains ALL context needed to continue work across sessions.

## Current State (as of March 11, 2026)

### What exists on the Pi RIGHT NOW
- **OS**: AgenC OS 2.0 (Yocto Scarthgap 5.0.16), read-only rootfs, BusyBox userland
- **Runtime**: Python voice agent (`agenc_voice_task.py`) — NOT the TypeScript framework
- **Node.js**: Installed in the image but UNUSED — no TypeScript runtime bundled
- **Voice pipeline**: arecord -> xAI Realtime WS (STT) -> Grok 4.20 -> xAI TTS -> aplay
- **Wallet**: Solana devnet, solders library, direct JSON-RPC (no solana-py)
- **Tools**: Python scripts (agenc-price, agenc-wallet, agenc-qr, agenc-display)
- **Phase 2 step #3** ("Node.js + Runtime") was only PARTIALLY completed — Node.js recipe exists but runtime was never bundled

### What needs to happen
Replace the Python voice agent with the full @agenc/runtime TypeScript framework running natively as the OS's primary process.

---

## Project Directories (Mac)

| Path | What |
|---|---|
| `/Users/pchmirenko/Desktop/agenc-one-repo/` | Yocto build system, meta-agenc layer, THIS file |
| `/Users/pchmirenko/Desktop/agenc-one-docs/` | Device docs (setup, voice pipeline, wallet, bugs) |
| `/Users/pchmirenko/Desktop/AgenC/` | @agenc/runtime + @agenc/sdk source (from github.com/tetsuo-ai/AgenC) |
| `/Users/pchmirenko/Desktop/AgenC/runtime/` | Runtime source (~90k lines TypeScript) |
| `/Users/pchmirenko/Desktop/AgenC/sdk/` | Solana SDK (pure TypeScript, Anchor client) |
| `/Users/pchmirenko/Desktop/agenc-one-landing/` | agencone.com landing page |
| `/Users/pchmirenko/Desktop/AgenC-Operator/` | Android app (Tauri v2) |
| `/Users/pchmirenko/Desktop/suit-cases/` | 3D printable case models (PiSugar3 + WhisPlay + Pi Zero) |
| `/Users/pchmirenko/agenc_voice_task.py` | Current Python voice agent (deployed to Pi via SCP) |

---

## Pi Device Access

- **IP**: Dynamic (was 192.168.178.48, then .54, then .59 — changes on DHCP lease)
- **WiFi**: "Santa Helena" / "YOUR_WIFI_PASSWORD"
- **Root password**: `agenc`
- **SSH**: `sshpass -p "agenc" ssh -o StrictHostKeyChecking=no root@<IP>`
- **SCP**: `sshpass -p "agenc" scp -O -o StrictHostKeyChecking=no <file> root@<IP>:<dest>` (needs `-O` for BusyBox)
- **Host key changes every boot** (Dropbear on tmpfs) — run `ssh-keygen -R <IP>` before connecting
- **No RTC** — clock resets every boot, SSL fails if wrong. Fix: `date -s "2026-03-11 HH:MM:00"` or NTP
- **BusyBox caveats**: `head -n 15` (not `head -15`), `ps` (not `ps aux`), many GNU flags missing

### Key Paths on Pi
```
/opt/agenc/agenc_voice_task.py    # Current Python voice agent (rootfs, read-only)
/opt/agenc/WhisPlay.py            # Display/GPIO driver (ST7789 SPI)
/opt/agenc/agenc-display.py       # Display text helper
/opt/agenc/scripts/               # Utility scripts (price, wallet, qr)
/data/keystore/wallet.json        # Solana wallet (writable partition)
/data/agenc/env                   # Environment vars (XAI_API_KEY, etc.)
/data/agenc/pylib/                # pip-installed Python packages
/data/agenc/logs/                 # Agent logs
/lib/systemd/system/agenc-runtime.service  # systemd service
/etc/systemd/system/agenc-runtime.service.d/no-watchdog.conf  # watchdog override
```

### Systemd Service Commands
```bash
systemctl restart agenc-runtime.service
systemctl reset-failed agenc-runtime.service    # if rate-limited
journalctl -u agenc-runtime.service -n 30 --no-pager
```

---

## @agenc/runtime Architecture (TypeScript Framework)

Source: `/Users/pchmirenko/Desktop/AgenC/runtime/`

### Entry Point
- `src/bin/agenc-runtime.ts` → calls `runCli()` from `src/cli/index.ts`
- CLI commands: `start` (daemon), `start --foreground` (systemd mode), `stop`, `status`, `health`, `logs`, `sessions`, `onboard`
- **Foreground mode** (`--foreground`) is what we use on the Pi — blocks with `new Promise<void>(() => {})`

### Core Services (wired in `src/gateway/daemon.ts`)
1. **Gateway** (`gateway.ts`) — HTTP API, routes requests
2. **ChatExecutor** (`src/llm/chat-executor.ts`) — LLM conversation engine
3. **ToolRegistry** (`src/tools/registry.ts`) — 40+ tools
4. **VoiceBridge** (`src/gateway/voice-bridge.ts`) — xAI Realtime WebSocket, Chat-Supervisor pattern
5. **SessionManager** (`src/gateway/session.ts`) — user session tracking
6. **MemoryBackend** (`src/memory/`) — SQLite, Redis, or in-memory
7. **Channels** (`src/channels/`) — Discord, Telegram, Slack, WhatsApp, Matrix, iMessage, Signal, Webchat

### LLM Providers (`src/llm/`)
- **Grok** (`src/llm/grok/`) — via xAI API (OpenAI-compatible)
- **Ollama** (`src/llm/ollama/`) — local models (NOT viable on Pi Zero 2W)
- Executor with fallback chain, token budgets, delegation decisions

### Voice System (`src/voice/`)
- **Realtime client** (`src/voice/realtime/client.ts`) — `XaiRealtimeClient`, connects to `wss://api.x.ai/v1/realtime`
- **STT** (`src/voice/stt.ts`) — speech-to-text
- **TTS** (`src/voice/tts.ts`) — text-to-speech via xAI TTS API
- PCM 24kHz audio, base64 encoded over WebSocket

### Tools (`src/tools/`)
- **System**: bash, browser, filesystem, http, macos
- **AgenC**: on-chain tools (agenc-tools.ts)
- **Social**: social media tools
- **X/Twitter**: posting, reading timeline
- **Marketplace**: tool marketplace
- **Skill adapter**: skill-adapter.ts

### Dependencies
**Required** (2 packages):
- `@agenc/sdk` (local, pure TypeScript)
- `@modelcontextprotocol/sdk` ^1.26.0

**Optional** (lazy-loaded, 13 packages):
- `better-sqlite3` ^12.0.0 — **INCLUDE** (memory backend, needs ARM cross-compile)
- `ws` ^8.0.0 — **INCLUDE** (WebSocket for voice)
- `edge-tts` ^1.0.0 — **INCLUDE** (TTS fallback)
- `cheerio` ^1.0.0 — **INCLUDE** (HTML parsing for browser tool)
- `openai` ^4.0.0 — **EXCLUDE** (use Grok direct, OpenAI-compatible)
- `ollama` ^0.5.0 — **EXCLUDE** (can't run local models on Pi Zero)
- `playwright` ^1.40.0 — **EXCLUDE** (use Cloudflare Browser Rendering instead)
- `discord.js` ^14.7.0 — **EXCLUDE** (not needed on device)
- `grammy` ^1.0.0 — **EXCLUDE** (Telegram, not needed)
- `@slack/bolt` ^4.0.0 — **EXCLUDE** (not needed)
- `@whiskeysockets/baileys` ^6.0.0 — **EXCLUDE** (WhatsApp, not needed)
- `matrix-js-sdk` ^34.0.0 — **EXCLUDE** (not needed)
- `ioredis` ^5.0.0 — **EXCLUDE** (use SQLite on device)

### Build Command
```bash
cd /Users/pchmirenko/Desktop/AgenC/runtime
npm ci --production
npx tsup  # outputs to dist/ (CJS + ESM, ~30MB bundle)
```

tsup config externalizes all optional deps. Output is pure JavaScript — runs on any arch.

---

## Yocto Build System

### Build Pipeline — Lima VM (ACTUAL BUILD METHOD)
```
Mac: limactl start yocto    (Lima VM: Ubuntu 22.04, 8 CPU, 12GB RAM, 100GB disk)
  └── VM has Mac filesystem mounted at /Users/pchmirenko via virtiofs
        ~/poky/                         ← Yocto core (scarthgap)
        ~/meta-raspberrypi/             ← Pi BSP layer (scarthgap)
        ~/meta-openembedded/            ← OE layers (scarthgap)
        ~/poky/meta-agenc/              ← OUR LAYER (synced from Mac via rsync)
        ~/poky/build-agenc/             ← Build dir (local.conf, sstate-cache, tmp/)
              │
              source oe-init-build-env build-agenc && bitbake agenc-os-image
              │
              └── Output: ~/poky/build-agenc/tmp/deploy/images/agenc-one/
                    └── agenc-os-image-agenc-one.wic
```

### Lima VM Commands
```bash
# Start/stop VM
limactl start yocto
limactl stop yocto

# Shell into VM
limactl shell yocto

# Sync meta-agenc from Mac to VM
limactl shell yocto -- rsync -av --delete /Users/pchmirenko/Desktop/agenc-one-repo/meta-agenc/ ~/poky/meta-agenc/

# Run build inside VM
limactl shell yocto -- bash -lc 'cd ~/poky && source oe-init-build-env build-agenc > /dev/null 2>&1 && bitbake agenc-os-image'
```

### VM Build Config
- **local.conf**: MACHINE="agenc-one", INIT_MANAGER="systemd", BB_NUMBER_THREADS=8, PARALLEL_MAKE="-j 8"
- **local.conf**: LICENSE_FLAGS_ACCEPTED="synaptics-killswitch commercial" (WiFi firmware)
- **bblayers.conf**: 8 layers (core, poky, yocto-bsp, raspberrypi, oe, python, networking, meta-agenc)
- **sstate-cache**: `~/poky/build-agenc/sstate-cache/` (persists across builds)
- **downloads**: `~/poky/build-agenc/downloads/` (includes RPi kernel git mirror ~3GB)

### Docker Build Method (ALTERNATIVE, not currently used)
```bash
cd /Users/pchmirenko/Desktop/agenc-one-repo
./yocto/build.sh

# Flash to SD
bzcat ~/.agenc-yocto-cache/tmp/deploy/images/agenc-one/agenc-os-image-agenc-one.wic.bz2 \
  | sudo dd of=/dev/rdiskN bs=4m

# Factory provision
./scripts/factory-provision.sh /dev/diskN "Santa Helena" "YOUR_WIFI_PASSWORD"
```

### Partition Layout (`meta-agenc/wic/agenc-os.wks`)
| # | Mount | Size | FS | Purpose |
|---|---|---|---|---|
| p1 | /boot | 64MB | vfat | kernel, DTBs, firmware |
| p2 | / | 512MB | ext4 | rootfs-a (active, read-only) |
| p3 | — | 512MB | ext4 | rootfs-b (OTA slot, empty) |
| p4 | /data | 256MB | ext4 | agent state, wallet, logs, config (writable) |

### Key Yocto Files
```
meta-agenc/
├── conf/
│   ├── layer.conf
│   └── machine/agenc-one.conf                    # Machine config (SPI, audio, GPIO, WiFi)
├── recipes-agenc/
│   ├── agenc-runtime/agenc-runtime_1.0.bb         # CURRENT: Python scripts (TO BE REPLACED)
│   └── agenc-config/agenc-config_1.0.bb           # /data mount, directory creation
├── recipes-core/
│   └── images/agenc-os-image.bb                   # Image manifest (what gets installed)
├── recipes-connectivity/
│   └── wifi/wifi-config_1.0.bb                    # wpa_supplicant config
├── recipes-security/
│   ├── dm-crypt/keystore-setup_1.0.bb             # LUKS keystore
│   └── firewall/nftables-rules_1.0.bb             # nftables firewall
├── recipes-support/
│   └── agenc-ota/agenc-ota_1.0.bb                 # RAUC OTA (commented out in image)
└── wic/
    └── agenc-os.wks                               # Partition layout
```

### Machine Config (`agenc-one.conf`)
- Base: `raspberrypi0-2w-64` (Pi Zero 2W, aarch64)
- SPI display: `dtoverlay=spi0-1cs`, `dtoverlay=st7789v`
- Audio: `dtoverlay=wm8960-soundcard`, `dtparam=i2c_arm=on`
- GPIO: libgpiod
- WiFi firmware: `linux-firmware-rpidistro-bcm43436`
- GPU: 16MB (no desktop)
- Silent boot: `quiet loglevel=0 logo.nologo`

### Current Image Manifest (`agenc-os-image.bb`)
Installs: `packagegroup-core-boot`, `kernel-modules`, `wpa-supplicant`, `dhcpcd`, `ntp`,
`ca-certificates`, `curl`, `nodejs`, `python3`, `python3-pip`, `python3-pillow`,
`alsa-utils/lib/plugins`, `libgpiod`, `i2c-tools`, `nftables`, `cryptsetup`,
`agenc-runtime` (Python), `agenc-config`, `wifi-config`, `dropbear`, `systemd`, `nano`, `htop`

---

## INTEGRATION PLAN

### Phase A — Runtime Nativo (Priority 1)

#### A1: Pre-build del runtime bundle
```bash
cd /Users/pchmirenko/Desktop/AgenC/runtime
npm ci --production
npx tsup
# Output: dist/bin/agenc-runtime.js, dist/index.js, dist/index.mjs
```
- Copy dist/ + filtered node_modules/ to recipe files dir
- Exclude dev deps, test files, .ts source

#### A2: Crear receta `agenc-node-runtime_1.0.bb`
- Location: `meta-agenc/recipes-agenc/agenc-node-runtime/`
- Files dir: `meta-agenc/recipes-agenc/agenc-node-runtime/files/`
- Installs pre-built bundle to `/opt/agenc/runtime/`
- Cross-compiles `better-sqlite3` for ARM64 (only native dep)
- RDEPENDS: `nodejs`
- Systemd service: `agenc-node-runtime.service`
  - `ExecStart=/usr/bin/node /opt/agenc/runtime/dist/bin/agenc-runtime.js --foreground`
  - `Restart=always`, `OOMScoreAdjust=-900`
  - `Environment=AGENC_CONFIG=/data/agenc/config.json`

#### A3: Hardware Bridge Tools (TypeScript)
Create new tools that replace Python scripts, registered in ToolRegistry:
- `display-tool.ts` — SPI display control via `/dev/spidev0.0` (replaces WhisPlay.py + agenc-display.py)
- `led-tool.ts` — RGB LED via `/sys/class/gpio/` or libgpiod
- `button-tool.ts` — GPIO interrupt for physical button
- `audio-tool.ts` — `arecord`/`aplay` wrapper for mic/speaker
- `price-tool.ts` — DexScreener API (replaces agenc-price)
- `wallet-tool.ts` — Solana wallet ops (replaces agenc-wallet)
- `qr-tool.ts` — QR code on display (replaces agenc-qr)

Location: `/Users/pchmirenko/Desktop/AgenC/runtime/src/tools/hardware/` (new directory)

#### A4: Update image recipe
In `agenc-os-image.bb`:
```
# BEFORE
IMAGE_INSTALL += " agenc-runtime agenc-config wifi-config "
# AFTER
IMAGE_INSTALL += " agenc-node-runtime agenc-config wifi-config "
```
- Remove or rename old `agenc-runtime` Python recipe
- Keep Python3 in image for backward compat (or remove to save ~20MB)

#### A5: Build image
```bash
cd /Users/pchmirenko/Desktop/agenc-one-repo
./yocto/build.sh
```
Output: `~/.agenc-yocto-cache/tmp/deploy/images/agenc-one/agenc-os-image-agenc-one.wic`

#### A6: Flash + test
```bash
bzcat <image>.wic.bz2 | sudo dd of=/dev/rdiskN bs=4m
./scripts/factory-provision.sh /dev/diskN "Santa Helena" "YOUR_WIFI_PASSWORD"
# Insert SD, power on, SSH in, verify:
systemctl status agenc-node-runtime.service
journalctl -u agenc-node-runtime.service -n 50 --no-pager
```

### Phase B — USB Provisioning CLI (Priority 2, parallel to A)

#### B1: USB Gadget Mode (`g_serial`)
- Pi Zero 2W supports USB OTG on data port
- Load `g_serial` kernel module on boot → exposes `/dev/ttyGS0`
- Pi appears as `/dev/cu.usbmodemXXXX` on Mac, `COM3` on Windows
- Add to machine config: `KERNEL_MODULE_AUTOLOAD += "g_serial"`
- Udev rule: start provisioning daemon when USB data connected

#### B2: Provisioning Daemon (Pi side)
- Runs on `/dev/ttyGS0` (serial over USB)
- Interactive menu:
  - WiFi → SSID + password → writes `/data/agenc/wifi.conf`
  - API Keys → xAI, Cloudflare → writes `/data/agenc/config.json`
  - Wallet → Generate new or import → `/data/keystore/wallet.json`
  - Voice → Select voice, language, mode (VAD/push-to-talk)
  - Network Test → Pi connects WiFi, reports result
  - Diagnostics → Hardware status (display, audio, battery, I2C)
- Writes ONLY to `/data/` (always writable)
- Works 100% offline via USB serial

#### B3: `agenc-cli` (Mac/PC side)
- Node.js CLI, distributed via `npx agenc-cli setup`
- Uses `serialport` npm package for USB serial communication
- Interactive UI with `inquirer` or `clack`
- Alternative: user can use `screen /dev/cu.usbmodemXXXX 115200` directly

#### B4: Yocto recipe `agenc-provision_1.0.bb`
- Configures `g_serial` module autoload
- Installs provisioning daemon script
- Udev rule for auto-start

### Phase C — Browser Tool via Cloudflare (Priority 3)

**Playwright is NOT feasible on Pi Zero 2W** (insufficient RAM, missing glibc, no ARM64 Chromium).

**Solution: Cloudflare Browser Rendering API** (announced March 10, 2026)
- Endpoint: `POST /client/v4/accounts/{account_id}/browser-rendering/crawl`
- Submits URL → Cloudflare renders in headless browser on edge → returns HTML/Markdown/JSON
- **Zero infrastructure needed** — no Chromium on Pi or server
- Available on Cloudflare Free plan
- API docs: https://developers.cloudflare.com/changelog/post/2026-03-10-br-crawl-endpoint/

#### C1: `browser-crawl` tool
- New tool in runtime ToolRegistry
- Makes HTTP POST to Cloudflare `/crawl` endpoint
- Polls job_id for results
- Returns markdown content to LLM for processing
- Config: `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` in `/data/agenc/config.json`

#### C2: Integration
- Agent says "look up X website" → browser-crawl tool fires → Cloudflare renders → markdown back → LLM processes
- ~50 lines of TypeScript, just HTTP calls via `undici`

### Execution Order

| Phase | Task | Depends on | Notes |
|---|---|---|---|
| **A1** | Pre-build runtime bundle (tsup) | — | Do first |
| **A2** | Create `agenc-node-runtime` recipe | A1 | New .bb file |
| **A3** | Hardware bridge tools (TS) | A1 | Can parallel with A2 |
| **A4** | Update `agenc-os-image.bb` | A2, A3 | Swap recipe |
| **A5** | Build image (`./yocto/build.sh`) | A4 | ~2hrs first time |
| **A6** | Flash + test on Pi | A5 | Validate |
| **B1** | USB gadget config | — | Independent of A |
| **B2** | Provisioning daemon | B1 | Pi side |
| **B3** | `agenc-cli` Mac/PC tool | B2 | User side |
| **B4** | Yocto recipe for provisioning | B2, A4 | Bundle in image |
| **C1** | Cloudflare browser-crawl tool | A1 | ~50 lines TS |
| **C2** | Integration + config | C1, A2 | Add to config schema |

---

## Hardware Details

### WhisPlay HAT
- **Display**: ST7789 SPI, 240x280 pixels, 1.69"
- **Audio codec**: WM8960 I2C (0x1a on i2c-1)
- **Mic gain**: +20dB (numid=9/8 = 2), ambient RMS ~200
- **Speaker volume**: numid=13 = 120,120
- **Button**: GPIO (libgpiod)
- **RGB LED**: GPIO controlled
- **Driver**: `WhisPlay.py` (mmap GPIO + spidev)

### PiSugar 3 Battery HAT
- **Status**: NOT detected on I2C (pogo pin contact issue with WhisPlay HAT)
- **Expected I2C**: 0x57 (MCU) + 0x68 (RTC DS3231)
- **LED**: Blue LED is ON (has power) but I2C not making contact
- **Fix needed**: Physical adjustment of pogo pins or manual wiring
- **3D cases**: `/Users/pchmirenko/Desktop/suit-cases/` (FDM version most practical)
  - `pisugar3-whisplay-chatbot-fdm/` — best fit for our hardware combo

### Solana Wallet
- **Address**: 5AVmqxRw47dLnsyfvh3iz5TQhCYKhTs35rreH3r6h9K2
- **Network**: Devnet
- **Token CA**: 5yC9BM8KUsJTPbWPLfA2N8qH1s9V8DQ3Vcw1G6Jdpump ($AGENC)
- **Wallet file**: `/data/keystore/wallet.json`

---

## Known Issues & Fixes

### Fixed
- **Watchdog kills service**: Override with `WatchdogSec=0` (survives reboots, NOT re-flashes)
- **WebSocket `additional_headers`**: Use `extra_headers=` (websockets v12+)
- **Import order crash**: `import sys` must be before `sys.path.insert()`
- **SCP fails**: Use `-O` flag (BusyBox has no sftp-server)
- **SSL cert errors**: Set clock manually (no RTC)
- **Service rate limited**: `systemctl reset-failed` before restart
- **No space for pip**: `TMPDIR=/data/tmp HOME=/data/tmp pip3 install --target=/data/agenc/pylib <pkg>`
- **VAD self-triggering**: 5s cooldown after speak(), lower mic gain
- **VAD not triggering**: Threshold 800 (4x ambient of ~200)

### Open Issues
- **On-chain memo fails**: `No module named 'solana'` — need solana-py or rewrite with raw RPC
- **Clock resets every boot**: No RTC, need NTP or manual `date -s`
- **PiSugar 3 not on I2C**: Pogo pins not making contact
- **Devnet airdrop rate limited**: Use faucet or manual deposit

---

## Voice Pipeline Config (Current Python, to be replaced by TS runtime)

```
Pipeline: arecord -> xAI Realtime WS (STT) -> Grok 4.20 -> xAI TTS API -> aplay
Models:
  STT: wss://api.x.ai/v1/realtime (grok-2-public)
  Brain: grok-4.20-experimental-beta-0304-non-reasoning
  TTS: https://api.x.ai/v1/tts (voices: eve, ara, rex, sal, leo)
VAD: 0.5s chunks, RMS threshold 800, 5s cooldown, 3s recording
Audio: 24kHz, S16_LE, mono, plughw:0,0
```

The @agenc/runtime already has voice bridge (`src/gateway/voice-bridge.ts`) and realtime client (`src/voice/realtime/client.ts`) that connect to the same xAI Realtime API. The Python voice agent gets completely replaced.

---

## Infrastructure

### Digital Ocean Droplet
- **IP**: 159.223.161.69 (hostname: "privatepussy")
- **SSH**: `ssh -i ~/.ssh/id_rsa_digitalocean root@159.223.161.69`
- **Hosts**: agencone.com + tetsuoarena.com
- **agencone.com**: Static HTML + Express API (port 3099), SQLite waitlist DB
- **tetsuoarena.com**: nginx reverse proxy → SSH tunnel → localhost:8081 (RoArm-M3 stream)

### Reverse SSH Tunnel (for tetsuoarena.com)
```bash
ssh -R 8081:localhost:8081 -N -f -i ~/.ssh/id_rsa_digitalocean root@159.223.161.69
```
Drops on network interruption — re-run to restore.

---

## Design Philosophy

From PHASE2-PLAN.md: **"The agent is not an application running on top of the OS — the agent IS the OS."**

- Agent runs as root — full hardware control
- Direct GPIO/SPI/I2C/audio access
- Read-only rootfs (can't corrupt system)
- LUKS-encrypted keystore (wallet keys protected)
- nftables firewall (minimal attack surface)
- A/B partition for OTA rollback
- Boot-to-agent target: < 5 seconds

---

## Config File Schema (for `/data/agenc/config.json`)

```json
{
  "llm": {
    "provider": "grok",
    "model": "grok-4.20-experimental-beta-0304-non-reasoning",
    "apiKey": "${XAI_API_KEY}",
    "maxTokens": 150,
    "temperature": 0.2
  },
  "voice": {
    "enabled": true,
    "mode": "vad",
    "vadThreshold": 800,
    "vadCooldown": 5.0,
    "recordSeconds": 3,
    "ttsVoice": "ara",
    "sttEndpoint": "wss://api.x.ai/v1/realtime",
    "ttsEndpoint": "https://api.x.ai/v1/tts"
  },
  "wallet": {
    "path": "/data/keystore/wallet.json",
    "network": "devnet",
    "rpcEndpoint": "https://api.devnet.solana.com"
  },
  "memory": {
    "backend": "sqlite",
    "path": "/data/agenc/memory.db"
  },
  "browser": {
    "provider": "cloudflare",
    "accountId": "${CLOUDFLARE_ACCOUNT_ID}",
    "apiToken": "${CLOUDFLARE_API_TOKEN}"
  },
  "hardware": {
    "display": { "type": "st7789", "spiDev": "/dev/spidev0.0", "width": 240, "height": 280 },
    "audio": { "device": "plughw:0,0", "sampleRate": 24000, "format": "S16_LE" },
    "button": { "gpioChip": "gpiochip0", "line": 4 },
    "led": { "gpioChip": "gpiochip0", "lines": { "r": 17, "g": 27, "b": 22 } }
  },
  "wifi": {
    "ssid": "",
    "psk": ""
  }
}
```

---

## Quick Reference Commands

```bash
# === BUILD ===
cd /Users/pchmirenko/Desktop/AgenC/runtime && npm ci && npx tsup
cd /Users/pchmirenko/Desktop/agenc-one-repo && ./yocto/build.sh

# === FLASH ===
bzcat <image>.wic.bz2 | sudo dd of=/dev/rdiskN bs=4m
./scripts/factory-provision.sh /dev/diskN "Santa Helena" "YOUR_WIFI_PASSWORD"

# === DEPLOY (current Python, pre-integration) ===
sshpass -p "agenc" scp -O -o StrictHostKeyChecking=no /Users/pchmirenko/agenc_voice_task.py root@<IP>:/opt/agenc/
sshpass -p "agenc" ssh -o StrictHostKeyChecking=no root@<IP> "systemctl reset-failed agenc-runtime.service 2>/dev/null; systemctl restart agenc-runtime.service"

# === DEBUG PI ===
sshpass -p "agenc" ssh -o StrictHostKeyChecking=no root@<IP>
journalctl -u agenc-runtime.service -n 50 --no-pager
cat /tmp/voice_agent.log
i2cdetect -y 1    # should show 0x1a (WM8960), optionally 0x57+0x68 (PiSugar3)
date -s "2026-03-11 HH:MM:00"   # fix clock if SSL fails

# === DIGITAL OCEAN ===
ssh -i ~/.ssh/id_rsa_digitalocean root@159.223.161.69
```
