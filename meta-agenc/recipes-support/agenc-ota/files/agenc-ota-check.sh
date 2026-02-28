#!/bin/sh
# AgenC OTA Update Check
# Polls update server for new firmware bundles

set -e

OTA_SERVER="${AGENC_OTA_SERVER:-https://ota.agencone.com}"
DEVICE_ID=$(cat /proc/cpuinfo | grep Serial | awk '{print $3}')
CURRENT_VERSION=$(cat /etc/agenc-version 2>/dev/null || echo "0.0.0")
BUNDLE_DIR="/data/agenc/ota"

mkdir -p "$BUNDLE_DIR"

echo "[OTA] Checking for updates... (current: $CURRENT_VERSION)"

# Check for available update
RESPONSE=$(curl -sf \
    -H "X-Device-ID: $DEVICE_ID" \
    -H "X-Current-Version: $CURRENT_VERSION" \
    "$OTA_SERVER/api/v1/check" 2>/dev/null || echo "")

if [ -z "$RESPONSE" ]; then
    echo "[OTA] Server unreachable or no updates available"
    exit 0
fi

# Parse response (simple key=value format)
NEW_VERSION=$(echo "$RESPONSE" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
BUNDLE_URL=$(echo "$RESPONSE" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)

if [ -z "$NEW_VERSION" ] || [ "$NEW_VERSION" = "$CURRENT_VERSION" ]; then
    echo "[OTA] Already up to date"
    exit 0
fi

echo "[OTA] New version available: $NEW_VERSION"

# Download bundle
BUNDLE_PATH="$BUNDLE_DIR/agenc-os-$NEW_VERSION.raucb"
curl -sf -o "$BUNDLE_PATH" "$BUNDLE_URL"

# Install via RAUC
echo "[OTA] Installing update..."
rauc install "$BUNDLE_PATH"

# Clean up
rm -f "$BUNDLE_PATH"

echo "[OTA] Update installed. Reboot required."
