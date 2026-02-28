SUMMARY = "AgenC ONE Device Configuration"
DESCRIPTION = "Base configuration, user setup, and data partition mount for AgenC ONE"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c84e74ca1e4a5830e4dc9e7a7e91cf9b"

SRC_URI = " \
    file://agenc-data.mount \
    file://agenc-dirs.service \
    file://agenc-user.conf \
"

inherit useradd systemd

# Create agenc system user
USERADD_PACKAGES = "${PN}"
USERADD_PARAM:${PN} = "-r -d /data/agenc -s /bin/false -G gpio,spi,i2c,audio,video agenc"

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
