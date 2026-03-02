# Phase 2 Execution Plan — AgenC OS

## Design Philosophy: Native Agent Integration

The agent is not an application running on top of the OS — **the agent IS the OS**. AgenC OS exists for one purpose: to run the agent. Every design decision follows from this:

- **Agent runs as root** — no sandboxed user, no capability restrictions, no filesystem jails. The agent has full control over the hardware it was built for.
- **Direct hardware access** — GPIO, SPI, I2C, audio, display. No group membership hacks, no udev rules, no permission workarounds.
- **System management** — the agent can restart WiFi, trigger OTA updates, manage Bluetooth, read system logs, and control its own lifecycle.
- **Security through architecture, not isolation** — the OS protects itself through:
  - Read-only rootfs (agent can't corrupt the system even as root)
  - LUKS-encrypted keystore (wallet keys protected at rest)
  - nftables firewall (network attack surface minimized)
  - Signed OTA updates (can't install tampered code)
  - A/B rollback (bad update = automatic recovery)

This is the same model used by embedded systems, routers, and IoT devices: the firmware IS the application. Process-level sandboxing is for multi-tenant servers, not single-purpose hardware.

## Build Order (dependency chain)

```
#2 Yocto Environment ─────┬──→ #3 Node.js + Runtime
                          ├──→ #4 SPI Display Driver
                          ├──→ #5 ALSA Audio Pipeline ──→ #6 GPIO Button
                          └──→ #11 Network Hardening
                                      │
                          #3 + #4 + #5 + #6 ──→ #7 Read-only Rootfs
                                                       │
                                                 #7 ──→ #8 Encrypted Keys
                                                 #7 ──→ #9 Secure Boot
                                                       │
                                              #8 + #9 ──→ #10 OTA Updates
                                                              │
                                         #3 + #8 + #10 ──→ #12 Factory Provisioning
```

## Sprint 1 — Foundation (Week 1-2)

### Step 1: Yocto Build Environment (#2)
- Use Docker container on Mac (crops/poky) for cross-compilation
- Target: `raspberrypi0-2w-64` (Pi Zero 2W, aarch64)
- Layers: poky + meta-raspberrypi + meta-openembedded + meta-agenc
- Validate with `core-image-minimal` boot on Pi

### Step 2: Scaffold meta-agenc layer
```
meta-agenc/
├── conf/
│   ├── layer.conf
│   └── machine/agenc-one.conf
├── recipes-agenc/
│   ├── agenc-runtime/agenc-runtime_1.0.bb
│   └── agenc-config/agenc-config_1.0.bb
├── recipes-core/
│   ├── images/agenc-os-image.bb
│   └── systemd/agenc-runtime.service
├── recipes-connectivity/
│   └── wifi/wifi-config.bb
└── recipes-security/
    ├── dm-crypt/keystore-setup.bb
    └── firewall/nftables-rules.bb
```

## Sprint 2 — Hardware Integration (Week 2-3)

### Step 3: Node.js + Runtime (#3)
- Recipe for Node.js 22 LTS (meta-nodejs or custom)
- Bundle agenc_voice_task.py + dependencies as recipe
- systemd service: `agenc-runtime.service`

### Step 4: Hardware Drivers (#4, #5, #6)
- SPI display: device tree overlay + framebuffer config
- ALSA: minimal config, USB mic + speaker
- GPIO: libgpiod recipe, button handler integrated into runtime

## Sprint 3 — Security (Week 3-4)

### Step 5: Read-only Root (#7)
- overlayfs or dm-verity for rootfs
- /data partition for mutable state

### Step 6: Encrypted Keys (#8)
- dm-crypt for /data/keystore
- Key derivation from device serial

### Step 7: Secure Boot + Network (#9, #11)
- U-Boot verified boot
- nftables outbound-only firewall

## Sprint 4 — Updates & Provisioning (Week 4-5)

### Step 8: OTA System (#10)
- RAUC integration with A/B slots

### Step 9: Factory Provisioning (#12)
- Flash script + keypair generation + QA check

## Native Integration Checklist

- [x] Agent runs as root (no sandboxed user)
- [x] No ProtectSystem/ProtectHome/NoNewPrivileges restrictions
- [x] Direct GPIO/SPI/I2C/audio access without group hacks
- [x] OOMScoreAdjust=-900 (agent is highest priority process)
- [x] Restart=always (agent must never stop running)
- [x] Environment paths point to /data/ partition
- [ ] Agent can trigger RAUC OTA updates
- [ ] Agent can manage wpa_supplicant (WiFi config)
- [ ] Agent can manage Bluetooth connections
- [ ] Boot-to-agent time < 5 seconds
