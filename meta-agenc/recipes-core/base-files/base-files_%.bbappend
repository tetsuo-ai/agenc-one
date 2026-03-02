# AgenC OS: Base system configuration
# - /data mount point and fstab entries for read-only rootfs
# - Root SSH authorized_keys directory
# - Hostname and OS branding

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

do_install:append() {
    # Create mount points
    install -d ${D}/data

    # Add /data partition to fstab
    echo "/dev/mmcblk0p4  /data  ext4  defaults,noatime  0  2" >> ${D}${sysconfdir}/fstab

    # tmpfs mounts for volatile state
    echo "tmpfs  /tmp   tmpfs  defaults,nosuid,nodev,size=32M  0  0" >> ${D}${sysconfdir}/fstab
    echo "tmpfs  /run   tmpfs  defaults,nosuid,nodev,mode=755,size=16M  0  0" >> ${D}${sysconfdir}/fstab

    # Hostname
    echo "agenc-one" > ${D}${sysconfdir}/hostname

    # Hosts file
    cat > ${D}${sysconfdir}/hosts << 'EOF'
127.0.0.1   localhost
127.0.1.1   agenc-one
::1         localhost ip6-localhost ip6-loopback
EOF

    # SSH authorized_keys (populated during factory provisioning)
    install -d -m 0700 ${D}/root/.ssh
    install -m 0600 ${WORKDIR}/authorized_keys ${D}/root/.ssh/authorized_keys

    # OS identification
    cat > ${D}${sysconfdir}/os-release << 'EOF'
ID=agenc-os
NAME="AgenC OS"
VERSION="2.0 (Phase 2)"
VERSION_ID=2.0
PRETTY_NAME="AgenC OS 2.0 — TETSUO CORP"
HOME_URL="https://agencone.com"
BUILD_ID="${DATETIME}"
VARIANT="AGENC ONE"
VARIANT_ID=agenc-one
EOF

    # MOTD - shown on SSH login
    cat > ${D}${sysconfdir}/motd << 'MOTDEOF'

    ╔═══════════════════════════════════════╗
    ║          AGENC ONE · AgenC OS         ║
    ║       Autonomous AI Agent Device      ║
    ║           — TETSUO CORP —             ║
    ╚═══════════════════════════════════════╝

MOTDEOF

    # Issue (shown on serial console before login)
    cat > ${D}${sysconfdir}/issue << 'EOF'
AgenC OS 2.0 · AGENC ONE
\n \l

EOF
}

FILES:${PN} += "/root/.ssh /data"

SRC_URI += "file://authorized_keys"
