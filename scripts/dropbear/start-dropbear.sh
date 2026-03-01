#!/bin/sh
# AgenC OS - Dropbear SSH auto-setup
# Run on Pi after boot: sh /boot/dropbear/start-dropbear.sh
#
# This script installs Alpine Linux's musl-based dropbear SSH package
# and its dependencies onto the Yocto rootfs at runtime.
#
# Required files in /boot/dropbear/:
#   dropbear, dropbearkey, ld-musl-aarch64.so.1,
#   libutmps.so.0.1.2.3, libz.so.1.3.1, libskarnet.so.2.14.3.0

echo "[1/7] Remounting filesystem read-write..."
mount -o remount,rw /
if [ $? -ne 0 ]; then echo "FAILED to remount rw"; exit 1; fi

echo "[2/7] Installing musl libc..."
cp /boot/dropbear/ld-musl-aarch64.so.1 /lib/
ln -sf /lib/ld-musl-aarch64.so.1 /lib/libc.musl-aarch64.so.1

echo "[3/7] Installing shared libraries..."
cp /boot/dropbear/libutmps.so.0.1.2.3 /usr/lib/
ln -sf /usr/lib/libutmps.so.0.1.2.3 /usr/lib/libutmps.so.0.1
cp /boot/dropbear/libz.so.1.3.1 /usr/lib/
ln -sf /usr/lib/libz.so.1.3.1 /usr/lib/libz.so.1
cp /boot/dropbear/libskarnet.so.2.14.3.0 /usr/lib/
ln -sf /usr/lib/libskarnet.so.2.14.3.0 /usr/lib/libskarnet.so.2.14

echo "[4/7] Installing dropbear binaries..."
cp /boot/dropbear/dropbear /usr/sbin/dropbear
cp /boot/dropbear/dropbearkey /usr/bin/dropbearkey
chmod +x /usr/sbin/dropbear /usr/bin/dropbearkey

echo "[5/7] Generating host keys (ecdsa, rsa, ed25519)..."
mkdir -p /etc/dropbear
rm -f /etc/dropbear/dropbear_*_host_key
/usr/bin/dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key
/usr/bin/dropbearkey -t rsa -s 2048 -f /etc/dropbear/dropbear_rsa_host_key
/usr/bin/dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key

echo "[6/7] Setting root password..."
echo "Set a root password now:"
passwd

echo "[7/7] Starting dropbear SSH on port 22..."
grep -q '/bin/sh' /etc/shells 2>/dev/null || echo '/bin/sh' >> /etc/shells
/usr/sbin/dropbear -R -p 22

echo ""
echo "============================="
echo "SSH READY on port 22"
echo "============================="
