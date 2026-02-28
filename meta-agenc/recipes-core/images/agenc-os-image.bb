SUMMARY = "AgenC OS - Minimal agent execution image"
DESCRIPTION = "Purpose-built Linux image for AGENC ONE AI agent device"
LICENSE = "MIT"

inherit core-image

# Base system
IMAGE_INSTALL += " \
    packagegroup-core-boot \
    kernel-modules \
"

# Networking
IMAGE_INSTALL += " \
    wpa-supplicant \
    dhcpcd \
    ntp \
    ca-certificates \
    curl \
"

# Runtime dependencies
IMAGE_INSTALL += " \
    nodejs \
    python3 \
    python3-pip \
    python3-pillow \
    python3-pyserial \
"

# Audio
IMAGE_INSTALL += " \
    alsa-utils \
    alsa-lib \
    alsa-plugins \
"

# Hardware
IMAGE_INSTALL += " \
    libgpiod \
    libgpiod-tools \
    i2c-tools \
    spi-tools \
"

# Security
IMAGE_INSTALL += " \
    nftables \
    nftables-rules \
    cryptsetup \
    keystore-setup \
"

# Agent
IMAGE_INSTALL += " \
    agenc-runtime \
    agenc-config \
    wifi-config \
"

# OTA Updates
IMAGE_INSTALL += " \
    rauc \
    agenc-ota \
"

# System management
IMAGE_INSTALL += " \
    systemd \
    systemd-analyze \
    less \
    nano \
"

# Read-only root
IMAGE_FEATURES += "read-only-rootfs"

# Remove unnecessary features
IMAGE_FEATURES:remove = "splash"
BAD_RECOMMENDATIONS += "shared-mime-info"

# Image size control
IMAGE_ROOTFS_EXTRA_SPACE = "0"
IMAGE_OVERHEAD_FACTOR = "1.1"

# Partition layout
WKS_FILE = "agenc-os.wks"
