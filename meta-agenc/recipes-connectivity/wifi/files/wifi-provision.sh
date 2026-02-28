#!/bin/sh
# WiFi provisioning script for AgenC ONE
# Usage: wifi-provision.sh <SSID> <PSK>

set -e

SSID="$1"
PSK="$2"
CONF="/etc/wpa_supplicant/wpa_supplicant-wlan0.conf"

if [ -z "$SSID" ] || [ -z "$PSK" ]; then
    echo "Usage: $0 <SSID> <PSK>"
    exit 1
fi

# Generate network block
wpa_passphrase "$SSID" "$PSK" >> "$CONF"

# Persist credentials to data partition
echo "WIFI_SSID=$SSID" >> /data/agenc/env

# Reconfigure wpa_supplicant
wpa_cli -i wlan0 reconfigure

echo "WiFi configured for SSID: $SSID"
