# AgenC OS — Setup Guide

## Current State

AgenC OS is a custom Linux distribution running on a Raspberry Pi Zero 2W. SSH works out of the box. The agent runs as root — natively integrated into the OS, not sandboxed.

## System Info

| Field | Value |
|-------|-------|
| Board | Raspberry Pi Zero 2W |
| SoC | BCM2710A1 (ARM Cortex-A53, 64-bit) |
| Kernel | Linux 6.6.63-v8 aarch64 |
| OS | AgenC OS 2.0 (Yocto Scarthgap 5.0.16) |
| Hostname | agenc-one |
| SSH Port | 22 (Dropbear, socket-activated) |
| Root password | `agenc` |
| Agent | Runs as root via systemd (agenc-runtime.service) |

## Partition Layout

4 primary partitions on MBR:

```
/dev/mmcblk0p1  /boot   FAT32   64MB    Kernel, DTBs, firmware
/dev/mmcblk0p2  /       ext4    512MB   Root filesystem (read-only)
/dev/mmcblk0p3  -       ext4    512MB   OTA slot B (reserved)
/dev/mmcblk0p4  /data   ext4    256MB   Agent state, logs, config (read-write)
```

The root filesystem is mounted read-only. Writable directories are provided via volatile-binds (tmpfs-backed):

| Writable Path | Backing | Purpose |
|---------------|---------|---------|
| `/var/tmp` | tmpfs | Temporary files |
| `/var/cache` | tmpfs | Package cache |
| `/var/lib/systemd` | tmpfs | Systemd state |
| `/var/log` | tmpfs | System logs |
| `/etc/dropbear` | tmpfs | SSH host keys |

The `/data` partition is persistent across reboots and OTA updates:

```
/data/
├── agenc/          # Agent runtime state
│   ├── logs/       # Persistent agent logs
│   └── dropbear/   # (reserved for persistent SSH keys)
└── keystore/       # Wallet keys (future: LUKS encrypted)
```

## First Boot

1. Flash `agenc-os.wic` to SD card
2. Insert SD card into Pi Zero 2W
3. Connect ethernet (USB-to-ethernet adapter on data micro-USB port)
4. Power on
5. Pi boots, gets IP via DHCP, SSH is available immediately

## SSH Connection

```bash
ssh root@<PI_IP>
# Password: agenc
```

Or with sshpass for scripting:

```bash
sshpass -p 'agenc' ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no root@<PI_IP>
```

Find the Pi's IP via your router's DHCP table or:

```bash
# Check ARP table after Pi boots
arp -a | grep -i "e0:4c"
```

## SSH Details

Dropbear SSH is built into the image and starts automatically via systemd socket activation:

- `dropbear.socket` listens on port 22
- `dropbear@.service` handles each connection
- `dropbearkey.service` generates host keys on first boot
- Keys are stored in `/etc/dropbear/` (tmpfs, regenerated each boot)
- Root login enabled (default `-w` flag removed)

## Installed Packages

| Category | Packages |
|----------|----------|
| **Base** | packagegroup-core-boot, kernel-modules, systemd |
| **Network** | wpa-supplicant, dhcpcd, ntp, ca-certificates, curl |
| **Runtime** | nodejs, python3, python3-pip, python3-pillow, python3-pyserial |
| **Audio** | alsa-utils, alsa-lib, alsa-plugins |
| **Hardware** | libgpiod, libgpiod-tools, i2c-tools, python3-spidev |
| **Security** | nftables, nftables-rules, cryptsetup |
| **SSH** | dropbear |
| **Tools** | nano, htop, less, util-linux |

## Security Model

The agent runs as root by design. This is a single-purpose device — the agent IS the system.

| Layer | Protection |
|-------|-----------|
| **Rootfs** | Read-only ext4 — system can't be corrupted |
| **Firewall** | nftables — inbound blocked except SSH, outbound allowed |
| **Volatile state** | tmpfs-backed writable dirs, cleared on reboot |
| **Data partition** | Persistent `/data` for agent state only |

The agent has full access to: GPIO, SPI, I2C, audio, display, WiFi management, system services, and the `/data` partition.

## Firewall Rules

```
table inet agenc_filter {
    chain input {
        policy drop;
        iif "lo" accept                       # Loopback
        ct state established,related accept    # Return traffic
        tcp dport 22 accept                    # SSH
        udp sport 67 udp dport 68 accept       # DHCP
        counter drop                           # Everything else
    }
    chain output {
        policy accept;                         # All outbound allowed
    }
}
```

## Building

### Prerequisites

- Linux host or VM (Lima, Docker, or native)
- ~50GB disk space for Yocto build
- 8GB+ RAM recommended

### Local Build (Lima VM)

```bash
# Start Lima VM
limactl start yocto

# Enter VM
limactl shell yocto

# Source build environment
cd /path/to/poky
source oe-init-build-env /path/to/build

# Build image
bitbake agenc-os-image
```

Output: `tmp/deploy/images/raspberrypi0-2w-64/agenc-os-image-raspberrypi0-2w-64.rootfs.wic.bz2`

### Flash to SD Card

```bash
# Decompress
bunzip2 agenc-os-image-raspberrypi0-2w-64.rootfs.wic.bz2

# Flash (replace /dev/rdiskN with your SD card)
diskutil unmountDisk /dev/diskN
sudo dd if=agenc-os-image-*.wic of=/dev/rdiskN bs=4m status=progress
diskutil eject /dev/diskN
```

## Boot Splash

AgenC logo is displayed during boot via psplash. Kernel output is suppressed with `quiet loglevel=0 logo.nologo`.

## Known Limitations

1. **SSH host keys regenerated each boot** — `/etc/dropbear` is tmpfs-backed on read-only rootfs. Host key fingerprint changes on reboot.
2. **No package manager** — Minimal image has no opkg/apt. Software must be added via image rebuild.
3. **WiFi not configured** — wlan0 interface exists but needs wpa_supplicant configuration.
4. **OTA not yet active** — A/B partition layout is ready but RAUC integration pending (requires meta-rauc layer).
5. **Keystore not encrypted** — `/data/keystore` exists but LUKS encryption not yet configured.
