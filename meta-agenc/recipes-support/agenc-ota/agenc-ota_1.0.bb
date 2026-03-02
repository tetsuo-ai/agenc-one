SUMMARY = "AgenC ONE OTA Update Client"
DESCRIPTION = "Checks for and applies firmware updates via RAUC"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c79ff39f19dfec6d293b95dea7b07891"

SRC_URI = " \
    file://agenc-ota-check.sh \
    file://agenc-ota-check.service \
    file://agenc-ota-check.timer \
"

RDEPENDS:${PN} = "rauc curl"

inherit systemd

SYSTEMD_SERVICE:${PN} = "agenc-ota-check.timer"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}/opt/agenc/scripts
    install -m 0755 ${WORKDIR}/agenc-ota-check.sh ${D}/opt/agenc/scripts/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/agenc-ota-check.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${WORKDIR}/agenc-ota-check.timer ${D}${systemd_system_unitdir}/
}

FILES:${PN} = " \
    /opt/agenc/scripts/* \
    ${systemd_system_unitdir}/* \
"
