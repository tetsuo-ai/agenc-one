#!/bin/bash
# Fetch Dropbear SSH and dependencies from Alpine Linux for aarch64
# Run on macOS/Linux build machine, then copy output to SD card boot partition
set -e

ALPINE_VERSION="v3.21"
ALPINE_REPO="https://dl-cdn.alpinelinux.org/alpine/${ALPINE_VERSION}/main/aarch64"
OUT_DIR="${1:-./dropbear-bundle}"

mkdir -p "$OUT_DIR" /tmp/dropbear-fetch

echo "Fetching Alpine aarch64 packages..."

# Download packages
curl -L -o /tmp/dropbear-fetch/dropbear.apk "${ALPINE_REPO}/$(curl -sL ${ALPINE_REPO}/ | grep -o 'dropbear-[0-9][^"]*\.apk' | head -1)"
curl -L -o /tmp/dropbear-fetch/musl.apk "${ALPINE_REPO}/$(curl -sL ${ALPINE_REPO}/ | grep -o 'musl-[0-9][^"]*\.apk' | grep -v dev | head -1)"
curl -L -o /tmp/dropbear-fetch/zlib.apk "${ALPINE_REPO}/$(curl -sL ${ALPINE_REPO}/ | grep -o 'zlib-[0-9][^"]*\.apk' | grep -v dev | head -1)"
curl -L -o /tmp/dropbear-fetch/utmps.apk "${ALPINE_REPO}/$(curl -sL ${ALPINE_REPO}/ | grep -o 'utmps-libs-[^"]*\.apk' | head -1)"
curl -L -o /tmp/dropbear-fetch/skalibs.apk "${ALPINE_REPO}/$(curl -sL ${ALPINE_REPO}/ | grep -o 'skalibs-libs-[^"]*\.apk' | head -1)"

echo "Extracting binaries and libraries..."

# Extract each package
for pkg in dropbear musl zlib utmps skalibs; do
    mkdir -p /tmp/dropbear-fetch/$pkg
    cd /tmp/dropbear-fetch/$pkg
    tar xzf /tmp/dropbear-fetch/$pkg.apk 2>/dev/null || true
done

# Copy binaries
cp /tmp/dropbear-fetch/dropbear/usr/sbin/dropbear "$OUT_DIR/"
cp /tmp/dropbear-fetch/dropbear/usr/bin/dropbearkey "$OUT_DIR/"

# Copy libraries
cp /tmp/dropbear-fetch/musl/lib/ld-musl-aarch64.so.1 "$OUT_DIR/"
for lib in /tmp/dropbear-fetch/utmps/usr/lib/libutmps.so.*; do cp "$lib" "$OUT_DIR/"; done
for lib in /tmp/dropbear-fetch/zlib/usr/lib/libz.so.*; do cp "$lib" "$OUT_DIR/"; done
for lib in /tmp/dropbear-fetch/skalibs/usr/lib/libskarnet.so.*; do cp "$lib" "$OUT_DIR/"; done

# Copy setup script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/start-dropbear.sh" "$OUT_DIR/"

echo "Done. Copy $OUT_DIR/ to the SD card boot partition as /boot/dropbear/"
ls -lh "$OUT_DIR/"

# Cleanup
rm -rf /tmp/dropbear-fetch
