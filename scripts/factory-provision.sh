#!/bin/bash
# AgenC ONE Factory Provisioning Script
# Flashes AgenC OS image, generates keypair, configures WiFi
#
# Usage: ./factory-provision.sh <SD_DEVICE> <WIFI_SSID> <WIFI_PSK>
# Example: ./factory-provision.sh /dev/disk4 "MyNetwork" "password123"

set -e

IMAGE_DIR="${IMAGE_DIR:-./build/deploy/images/agenc-one}"
IMAGE_FILE="$IMAGE_DIR/agenc-os-image-agenc-one.wic"
SD_DEVICE="$1"
WIFI_SSID="$2"
WIFI_PSK="$3"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[PROVISION]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Validate args
[ -z "$SD_DEVICE" ] && error "Usage: $0 <SD_DEVICE> <WIFI_SSID> <WIFI_PSK>"
[ -z "$WIFI_SSID" ] && error "WiFi SSID required"
[ -z "$WIFI_PSK" ] && error "WiFi PSK required"
[ -f "$IMAGE_FILE" ] || error "Image not found: $IMAGE_FILE"
[ -b "$SD_DEVICE" ] || error "Not a block device: $SD_DEVICE"

# Safety check
warn "This will ERASE ALL DATA on $SD_DEVICE"
read -p "Type 'yes' to continue: " CONFIRM
[ "$CONFIRM" = "yes" ] || error "Aborted"

# Step 1: Flash image
log "Flashing AgenC OS image..."
if [[ "$(uname)" == "Darwin" ]]; then
    diskutil unmountDisk "$SD_DEVICE"
    sudo dd if="$IMAGE_FILE" of="${SD_DEVICE/disk/rdisk}" bs=4M status=progress
    sync
else
    sudo dd if="$IMAGE_FILE" of="$SD_DEVICE" bs=4M status=progress
    sync
fi
log "Image flashed"

# Step 2: Mount data partition (p4)
log "Mounting data partition..."
if [[ "$(uname)" == "Darwin" ]]; then
    sleep 2
    DATA_PART="${SD_DEVICE}s4"
    MOUNT_POINT=$(mktemp -d)
    diskutil mount -mountPoint "$MOUNT_POINT" "$DATA_PART"
else
    DATA_PART="${SD_DEVICE}p4"
    MOUNT_POINT=$(mktemp -d)
    sudo mount "$DATA_PART" "$MOUNT_POINT"
fi

# Step 3: Create directory structure
log "Creating agent directories..."
sudo mkdir -p "$MOUNT_POINT/agenc/logs"
sudo mkdir -p "$MOUNT_POINT/keystore"

# Step 4: Generate Solana keypair
log "Generating Solana keypair..."
if command -v solana-keygen &> /dev/null; then
    solana-keygen new --no-bip39-passphrase -o "$MOUNT_POINT/keystore/wallet.json" --force
    PUBKEY=$(solana-keygen pubkey "$MOUNT_POINT/keystore/wallet.json")
    log "Wallet: $PUBKEY"
else
    warn "solana-keygen not found - generating with Python"
    python3 -c "
from solders.keypair import Keypair
import json
kp = Keypair()
with open('$MOUNT_POINT/keystore/wallet.json', 'w') as f:
    json.dump(list(bytes(kp)), f)
print(f'Wallet: {kp.pubkey()}')
"
fi

# Step 5: Configure WiFi
log "Configuring WiFi: $WIFI_SSID"
sudo bash -c "cat > $MOUNT_POINT/agenc/env << EOF
WIFI_SSID=$WIFI_SSID
XAI_API_KEY=
AGENC_WALLET_PATH=/data/keystore/wallet.json
AGENC_TASKS_FILE=/data/agenc/tasks.json
AGENC_LOG_FILE=/data/agenc/logs/agent.log
EOF"

# Generate wpa_supplicant network block
WPA_CONF="$MOUNT_POINT/agenc/wpa_network.conf"
wpa_passphrase "$WIFI_SSID" "$WIFI_PSK" 2>/dev/null | sudo tee "$WPA_CONF" > /dev/null || \
    sudo bash -c "echo -e 'network={\n\tssid=\"$WIFI_SSID\"\n\tpsk=\"$WIFI_PSK\"\n}' > $WPA_CONF"

# Step 6: Set permissions
log "Setting permissions..."
sudo chmod 700 "$MOUNT_POINT/keystore"
sudo chmod 600 "$MOUNT_POINT/agenc/env"

# Step 7: Create version file on boot partition
if [[ "$(uname)" == "Darwin" ]]; then
    BOOT_PART="${SD_DEVICE}s1"
    BOOT_MOUNT=$(mktemp -d)
    diskutil mount -mountPoint "$BOOT_MOUNT" "$BOOT_PART"
else
    BOOT_PART="${SD_DEVICE}p1"
    BOOT_MOUNT=$(mktemp -d)
    sudo mount "$BOOT_PART" "$BOOT_MOUNT"
fi

VERSION=$(date +%Y%m%d)
echo "$VERSION" | sudo tee "$BOOT_MOUNT/agenc-version" > /dev/null

# Step 8: Unmount
log "Unmounting..."
if [[ "$(uname)" == "Darwin" ]]; then
    diskutil unmountDisk "$SD_DEVICE"
else
    sudo umount "$MOUNT_POINT" "$BOOT_MOUNT"
fi

# Done
log "========================================="
log "AgenC ONE provisioned successfully!"
log "========================================="
log "Version:  $VERSION"
log "WiFi:     $WIFI_SSID"
log "Wallet:   ${PUBKEY:-check device}"
log ""
log "Insert SD card into device and power on."
log "========================================="
