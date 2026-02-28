SUMMARY = "AgenC ONE Encrypted Keystore"
DESCRIPTION = "dm-crypt setup for /data/keystore encrypted volume"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c84e74ca1e4a5830e4dc9e7a7e91cf9b"

SRC_URI = " \
    file://keystore-init.sh \
    file://keystore-unlock.service \
"

RDEPENDS:${PN} = "cryptsetup"

inherit systemd

SYSTEMD_SERVICE:${PN} = "keystore-unlock.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}/opt/agenc/scripts
    install -m 0755 ${WORKDIR}/keystore-init.sh ${D}/opt/agenc/scripts/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/keystore-unlock.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} = " \
    /opt/agenc/scripts/* \
    ${systemd_system_unitdir}/keystore-unlock.service \
"
