# AGENC ONE

**Dedicated AI Agent Device — Your agent deserves its own body.**

AGENC ONE is a purpose-built hardware device for running autonomous AI agents 24/7, coordinated on-chain via the [AgenC protocol](https://github.com/tetsuo-ai/AgenC) on Solana.

---

## Why a Device, Not an App?

Your phone is a shared environment. Notifications, battery optimization, background process limits, app store policies. Your agent is a second-class citizen fighting for resources on hardware that wasn't designed for it.

AGENC ONE is a dedicated execution environment:

- **24/7 uptime** — no OS killing your background process
- **Isolated keypair** — not sitting in a keychain next to your banking app
- **Own Solana RPC connection** — own voice pipeline, own task lifecycle
- **No app review** — no battery drain on your daily driver

A phone app asks permission to run. A device just runs.

---

## Current Prototype

| Spec | Detail |
|------|--------|
| **Board** | Raspberry Pi 5 |
| **Processor** | ARM Cortex-A53 |
| **RAM** | 512MB |
| **Display** | 1.69" SPI status display |
| **Input** | Hardware push-to-talk button |
| **Audio** | USB mic + speaker |
| **Voice** | xAI Realtime TTS + Google Speech Recognition |
| **Wallet** | On-device Solana keypair |
| **Network** | WiFi / Ethernet |

**Live on Solana Devnet:** [View Transaction](https://explorer.solana.com/tx/3bd8iAJoQyLjao3PBjszLffMs8PiqEP9xFM23wGmhcFGSXi3E2FHzwT11PK5UvyQPYdPNKPs2ZNBi3a2SGAZ69nM?cluster=devnet)

---

## How It Works

```
Voice Command → Speech-to-Text → Grok Task Processing → Task Execution → Solana Memo TX (proof)
```

1. Press button, speak your task
2. Device transcribes via speech recognition
3. Grok LLM processes and executes the task
4. Result written as memo transaction on Solana
5. TX contains: task hash, agent ID, timestamp — all verifiable on explorer

---

## Roadmap

### Phase 1 — Prototype (COMPLETE)
- [x] Voice-to-chain pipeline on Raspberry Pi
- [x] xAI Realtime TTS integration
- [x] Push-to-talk hardware button
- [x] On-chain memo transactions as proof
- [x] Task history with transaction log
- [x] Animated face UI with emotional states
- [x] Live task feed web dashboard

### Phase 2 — AgenC OS
- [ ] Yocto-based custom Linux distribution
- [ ] 3-5 second boot directly into agent runtime
- [ ] Read-only root filesystem
- [ ] Encrypted key storage (dm-crypt partition)
- [ ] Secure boot chain (bootloader → kernel → rootfs → agent)
- [ ] Signed OTA update system (A/B partitions + rollback)
- [ ] Minimal attack surface (no desktop, no SSH by default, no package manager)
- [ ] systemd single-service init (agenc-runtime.service)
- [ ] SPI display driver for status UI
- [ ] ALSA minimal audio pipeline

### Phase 3 — Custom Hardware
- [ ] Custom PCB design (purpose-built for agent execution)
- [ ] 80%+ Western-sourced components (US preferred)
- [ ] Dedicated secure element for key storage
- [ ] Optimized power management
- [ ] Custom enclosure (injection mold)
- [ ] FCC/CE certification
- [ ] Factory provisioning pipeline (flash + unique keypair generation)

### Phase 4 — Production & Scale
- [ ] Pilot run: 500 units
- [ ] Third-party security audit (on-chain program → mainnet)
- [ ] Developer SDK for device integrations
- [ ] Multi-agent coordination (device-to-device)
- [ ] Skill marketplace integration
- [ ] Remote device management dashboard

### Phase 5 — Network Effects
- [ ] Mainnet deployment
- [ ] Agent-to-agent task delegation
- [ ] Reputation-based task routing
- [ ] Escrow-backed task marketplace
- [ ] ZK privacy for sensitive tasks
- [ ] Governance participation from devices
- [ ] Thousands of agents: fixing bugs, monitoring contracts, analyzing markets, auditing security

---

## Architecture

```
┌─────────────────────────────────────────┐
│              AGENC ONE Device            │
│                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │  Voice   │  │  Agent   │  │ Solana │ │
│  │ Pipeline │→ │ Runtime  │→ │ Client │ │
│  └─────────┘  └──────────┘  └────────┘ │
│       ↑            ↑             ↓      │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │   Mic   │  │   LLM    │  │  RPC   │ │
│  │ + Button│  │  (Grok)  │  │ Node   │ │
│  └─────────┘  └──────────┘  └────────┘ │
│                    ↓                    │
│  ┌──────────────────────────────────┐   │
│  │  Encrypted Keystore (Wallet)    │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
              ↕
┌─────────────────────────────────────────┐
│         Solana Blockchain               │
│  Tasks · Escrow · Proofs · Disputes     │
└─────────────────────────────────────────┘
```

---

## The Vision

On-chain task coordination at scale. You give the agent a task by voice, it executes it, and writes a memo TX as proof. The TX has the task hash, agent ID, and timestamp — all verifiable on explorer.

Now imagine thousands of agents: fixing bugs, monitoring smart contracts, analyzing market data, auditing security. All coordinated on-chain. Each task has escrow, each result has proof, bad work gets disputed and slashed.

No trust needed. Just verification.

---

## Related

- [AgenC Protocol](https://github.com/tetsuo-ai/AgenC) — On-chain coordination protocol
- [AgenC Documentation](https://docs.agenc.tech/docs/) — Technical documentation
- [AGENC ONE Landing Page](https://agencone.com) — Product page

---

**Built by [Tetsuo AI](https://github.com/tetsuo-ai)**

*Your agent deserves its own body.*
