# Phase 2 Execution Plan — AgenC OS

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
