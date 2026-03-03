# AgenC OS: Base system configuration
# - /data mount point and fstab entries for read-only rootfs
# - Root SSH authorized_keys directory
# - Hostname and OS branding
# - Colored MOTD and centered login issue

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

    # MOTD - colored ASCII art banner
    cat > ${D}${sysconfdir}/motd << 'MOTDEOF'

[1;36m     _    ____ _____ _   _  ____    ___  _   _ _____
    / \  / ___| ____| \ | |/ ___|  / _ \| \ | | ____|
   / _ \| |  _|  _| |  \| | |     | | | |  \| |  _|
  / ___ \ |_| | |___| |\  | |___  | |_| | |\  | |___
 /_/   \_\____|_____|_| \_|\____|  \___/|_| \_|_____|[0m

 [0;37mAgenC OS 2.0 | Autonomous Agent Runtime[0m
 [0;90mTETSUO CORP  | tetsuo.ai[0m

MOTDEOF

    # Issue - centered AGENC ONE on HDMI console
    printf '\e[2J\e[28;112H\e[1;34mA G E N C   O N E\e[0m\e[32;117H' > ${D}${sysconfdir}/issue

    # Profile - clear screen and show motd on login
    sed -i '1a\# Clear login screen\nclear\ncat /etc/motd\n' ${D}${sysconfdir}/profile || true
}

FILES:${PN} += "/root/.ssh /data"

SRC_URI += "file://authorized_keys"
