SUMMARY = "AgenC ONE Firewall Rules"
DESCRIPTION = "nftables outbound-only firewall for AgenC ONE device"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c84e74ca1e4a5830e4dc9e7a7e91cf9b"

SRC_URI = "file://agenc-firewall.nft"

RDEPENDS:${PN} = "nftables"

do_install() {
    install -d ${D}${sysconfdir}/nftables
    install -m 0644 ${WORKDIR}/agenc-firewall.nft ${D}${sysconfdir}/nftables/

    # Drop-in to load our ruleset at boot
    install -d ${D}${sysconfdir}/nftables.d
    install -m 0644 ${WORKDIR}/agenc-firewall.nft ${D}${sysconfdir}/nftables.d/agenc.nft
}

FILES:${PN} = " \
    ${sysconfdir}/nftables/* \
    ${sysconfdir}/nftables.d/* \
"
