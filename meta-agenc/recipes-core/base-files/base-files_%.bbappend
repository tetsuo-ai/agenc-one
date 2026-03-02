# AgenC OS: Base system configuration
# - /data mount point and fstab entries for read-only rootfs
# - Root SSH authorized_keys directory
# - Hostname and OS branding

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

do_install:append() {
    # Create mount points
    install -d ${D}/data

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

    # MOTD - shown on SSH login (pure ASCII for serial console compatibility)
    cat > ${D}${sysconfdir}/motd << 'MOTDEOF'

     _    ____ _____ _   _  ____    ___  _   _ _____
    / \  / ___| ____| \ | |/ ___|  / _ \| \ | | ____|
   / _ \| |  _|  _| |  \| | |     | | | |  \| |  _|
  / ___ \ |_| | |___| |\  | |___  | |_| | |\  | |___
 /_/   \_\____|_____|_| \_|\____|  \___/|_| \_|_____|

 AgenC OS 2.0 | Autonomous Agent Runtime
 TETSUO CORP  | tetsuo.ai

MOTDEOF

    # Issue (shown on serial console before login)
    cat > ${D}${sysconfdir}/issue << 'EOF'
AgenC OS 2.0
\n \l

EOF
}

FILES:${PN} += "/root/.ssh /data"

SRC_URI += "file://authorized_keys"
