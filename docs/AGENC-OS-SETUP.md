# AgenC OS — Pi Zero 2W Setup Guide

## Current State

AgenC OS is running on a Raspberry Pi Zero 2W with SSH access via Dropbear. The agent runs as root — natively integrated into the OS, not sandboxed.

## System Info

| Field | Value |
|-------|-------|
| Board | Raspberry Pi Zero 2W |
| SoC | BCM2710A1 (ARM Cortex-A53, 64-bit) |
| Kernel | Linux 6.6.63-v8 aarch64 |
| OS | Poky (Yocto) 5.0.16 "scarthgap" |
| Hostname | raspberrypi0-2w-64 |
| IP (LAN) | <PI_IP> (eth0, via USB ethernet adapter) |
| SSH Port | 22 (Dropbear) |
| WiFi | wlan0 detected, not configured |
| Agent | Runs as root via systemd (agenc-runtime.service) |

## SSH Connection

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no root@<PI_IP>
```

> Note: The macOS built-in `ssh` client may fail password auth intermittently with dropbear. Use `sshpass` for reliable connections.

## Boot Partition Layout

The FAT32 boot partition (`/boot` on Pi, `/Volumes/boot` on Mac) contains:

```
/boot/
├── bcm2710-rpi-zero-2.dtb    # Device tree for Pi Zero 2W
├── kernel8.img                 # 64-bit kernel
├── config.txt                  # Boot config
├── cmdline.txt                 # Kernel command line
├── overlays/                   # Device tree overlays
└── dropbear/                   # SSH package (Alpine musl-based)
    ├── dropbear                # SSH daemon binary
    ├── dropbearkey             # Key generation tool
    ├── ld-musl-aarch64.so.1   # musl libc
    ├── libutmps.so.0.1*       # utmp library
    ├── libz.so.1*             # zlib
    ├── libskarnet.so.2.14*    # skalibs (utmps dependency)
    └── start-dropbear.sh      # Setup + start script
```

## After Each Boot

The Yocto image boots to a maintenance shell (`sh-5.2#`). SSH is not started automatically. Run:

```bash
sh /boot/dropbear/start-dropbear.sh
```

This script:
1. Remounts root filesystem read-write
2. Copies musl libc and shared libraries to `/lib/` and `/usr/lib/`
3. Installs dropbear binaries to `/usr/sbin/` and `/usr/bin/`
4. Generates host keys (ecdsa, rsa, ed25519)
5. Sets root password
6. Starts dropbear SSH on port 22

## config.txt Additions

Added to original Yocto config for Pi Zero 2W compatibility:

```ini
# Pi Zero 2W boot config
arm_64bit=1
kernel=kernel8.img
device_tree=bcm2710-rpi-zero-2.dtb
enable_uart=1

# Force HDMI output
hdmi_force_hotplug=1
hdmi_drive=2
hdmi_group=1
hdmi_mode=16
config_hdmi_boost=4
gpu_mem=128
```

## Image Details

| Field | Value |
|-------|-------|
| Image file | `agenc-os.wic` (1.5GB) |
| Partitions | 4 (boot FAT32, rootfs ext4, secondary ext4, data ext4) |
| Boot partition | 87MB FAT32 |
| Root partition | 698MB ext4 (mmcblk0p2) |
| Target SD card | 256GB |
| Built with | Yocto Scarthgap 5.0.16, Docker-based build |

## Dropbear SSH Details

The Yocto image ships without SSH. We install Alpine Linux's dropbear package (musl-linked) at runtime:

- **Dropbear version**: 2024.86
- **Source**: Alpine Linux v3.21 aarch64 packages
- **Dependencies**: musl libc, libutmps, libz, libskarnet (all from Alpine)
- **Why Alpine**: Yocto rootfs uses glibc, but Alpine's musl-based dropbear is self-contained when bundled with musl libs

## Security Model

The agent runs as root by design. This is a single-purpose device — the agent IS the system. Security is enforced at the OS architecture level, not through process sandboxing:

| Layer | Protection |
|-------|-----------|
| **Rootfs** | Read-only ext4 — agent can't corrupt the system even as root |
| **Keystore** | LUKS-encrypted partition — wallet keys protected at rest |
| **Firewall** | nftables — outbound-only, minimal attack surface |
| **Updates** | Signed OTA via RAUC — can't install tampered code |
| **Rollback** | A/B partitions — bad update = automatic recovery |

The agent has full access to: GPIO, SPI, I2C, audio, display, WiFi management, Bluetooth, OTA triggers, system services, and `/data` partition.

## Known Issues

1. **Read-only root filesystem** — Must `mount -o remount,rw /` before any writes. The start-dropbear.sh script handles this.
2. **No package manager** — Minimal Yocto image has no opkg/apt/dnf. Software must be added via boot partition or image rebuild.
3. **EXT4 superblock warning** — `mmcblk0p4: unable to read superblock` appears during boot. Non-critical.
4. **Maintenance shell** — System drops to `sh-5.2#` instead of login prompt. This is expected for the minimal image.
5. **WiFi not configured** — wlan0 interface exists but needs wpa_supplicant configuration.

## SD Card Flashing

1. Use **Raspberry Pi Imager** → "Use custom" → select `.wic` or `.img` file
2. Or via `dd`: `sudo dd if=agenc-os.wic of=/dev/rdiskN bs=4m status=progress`
3. SD card adapter lock switch must be in **unlocked** position
4. macOS Terminal needs **Full Disk Access** for dd (System Settings → Privacy & Security)

## Network

- Pi Zero 2W has no built-in ethernet — uses USB-to-ethernet adapter on the data micro-USB port
- DHCP assigns IP on the LAN via the router
- mDNS/Bonjour not available (no avahi in image)
