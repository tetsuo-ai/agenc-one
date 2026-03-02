# AgenC OS: Dropbear SSH server configuration
# - Allow root login (override default -w flag)
# - Standard dropbearkey.service generates keys in /etc/dropbear
# - volatile-binds makes /etc/dropbear writable on read-only rootfs

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += "file://dropbear-agenc.default"

do_install:append() {
    # Override default config to allow root login
    install -d ${D}${sysconfdir}/default
    install -m 0644 ${WORKDIR}/dropbear-agenc.default ${D}${sysconfdir}/default/dropbear
}
