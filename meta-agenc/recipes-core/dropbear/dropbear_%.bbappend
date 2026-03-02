# AgenC OS: Dropbear SSH server configuration
# Enables root login, starts on boot, keys persisted to /data

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://dropbear-agenc.default \
    file://dropbear-keygen.service \
"

inherit systemd

SYSTEMD_SERVICE:${PN}:append = " dropbear-keygen.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install:append() {
    # Override default config
    install -d ${D}${sysconfdir}/default
    install -m 0644 ${WORKDIR}/dropbear-agenc.default ${D}${sysconfdir}/default/dropbear

    # Symlink host keys to /data so they persist across rootfs updates
    install -d ${D}${sysconfdir}/dropbear
    ln -sf /data/agenc/dropbear/dropbear_ecdsa_host_key ${D}${sysconfdir}/dropbear/dropbear_ecdsa_host_key
    ln -sf /data/agenc/dropbear/dropbear_ed25519_host_key ${D}${sysconfdir}/dropbear/dropbear_ed25519_host_key
    ln -sf /data/agenc/dropbear/dropbear_rsa_host_key ${D}${sysconfdir}/dropbear/dropbear_rsa_host_key

    # Install keygen service
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/dropbear-keygen.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} += "${systemd_system_unitdir}/dropbear-keygen.service"
