#!/bin/sh
# RAUC post-install hook for AgenC OS
# Runs after a new rootfs slot is written

set -e

echo "AgenC OS: Post-install hook running"

# Verify the new slot is mountable
SLOT_DEVICE="$RAUC_SLOT_DEVICE"
MOUNT_POINT="/mnt/rauc-verify"

mkdir -p "$MOUNT_POINT"
mount -o ro "$SLOT_DEVICE" "$MOUNT_POINT"

# Check critical files exist
for f in /opt/agenc/agenc_voice_task.py /usr/bin/python3; do
    if [ ! -f "${MOUNT_POINT}${f}" ]; then
        echo "ERROR: Missing critical file: $f"
        umount "$MOUNT_POINT"
        exit 1
    fi
done

umount "$MOUNT_POINT"
echo "AgenC OS: Post-install verification passed"
