SUMMARY = "AgenC ONE Device Configuration"
DESCRIPTION = "Base configuration and data partition mount for AgenC ONE"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c79ff39f19dfec6d293b95dea7b07891"

SRC_URI = " \
    file://agenc-data.mount \
    file://agenc-dirs.service \
    file://agenc-user.conf \
"

inherit systemd

# No separate user — the agent runs as root.
# This is a single-purpose device; the agent IS the system.

SYSTEMD_SERVICE:${PN} = "agenc-data.mount agenc-dirs.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    # systemd units
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/agenc-data.mount ${D}${systemd_system_unitdir}/
    install -m 0644 ${WORKDIR}/agenc-dirs.service ${D}${systemd_system_unitdir}/

    # tmpfiles.d for directory creation
    install -d ${D}${sysconfdir}/tmpfiles.d
    install -m 0644 ${WORKDIR}/agenc-user.conf ${D}${sysconfdir}/tmpfiles.d/
}

FILES:${PN} = " \
    ${systemd_system_unitdir}/* \
    ${sysconfdir}/tmpfiles.d/* \
"
