SUMMARY = "AgenC ONE WiFi Configuration"
DESCRIPTION = "WPA supplicant configuration and WiFi provisioning for AgenC ONE"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c79ff39f19dfec6d293b95dea7b07891"

SRC_URI = " \
    file://wpa_supplicant-wlan0.conf \
    file://wifi-provision.sh \
"

RDEPENDS:${PN} = "wpa-supplicant dhcpcd"

do_install() {
    # WPA supplicant base config (reads credentials from /data)
    install -d ${D}${sysconfdir}/wpa_supplicant
    install -m 0600 ${WORKDIR}/wpa_supplicant-wlan0.conf \
        ${D}${sysconfdir}/wpa_supplicant/

    # WiFi provisioning script
    install -d ${D}/opt/agenc/scripts
    install -m 0755 ${WORKDIR}/wifi-provision.sh ${D}/opt/agenc/scripts/
}

FILES:${PN} = " \
    ${sysconfdir}/wpa_supplicant/* \
    /opt/agenc/scripts/* \
"

CONFFILES:${PN} = "${sysconfdir}/wpa_supplicant/wpa_supplicant-wlan0.conf"
