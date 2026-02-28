#!/bin/sh
# Initialize encrypted keystore for AgenC ONE
# Run once during factory provisioning

set -e

KEYSTORE_DEV="/dev/mmcblk0p5"
KEYSTORE_NAME="agenc-keystore"
KEYSTORE_MOUNT="/data/keystore"

# Derive key from device serial (Pi CPU serial)
SERIAL=$(cat /proc/cpuinfo | grep Serial | awk '{print $3}')
KEY=$(echo -n "agenc-${SERIAL}" | sha256sum | awk '{print $1}')

# Format LUKS volume
echo -n "$KEY" | cryptsetup luksFormat "$KEYSTORE_DEV" -

# Open and format
echo -n "$KEY" | cryptsetup luksOpen "$KEYSTORE_DEV" "$KEYSTORE_NAME" -
mkfs.ext4 -L keystore "/dev/mapper/$KEYSTORE_NAME"

# Mount and set permissions
mkdir -p "$KEYSTORE_MOUNT"
mount "/dev/mapper/$KEYSTORE_NAME" "$KEYSTORE_MOUNT"
chown agenc:agenc "$KEYSTORE_MOUNT"
chmod 700 "$KEYSTORE_MOUNT"

echo "Keystore initialized at $KEYSTORE_MOUNT"
