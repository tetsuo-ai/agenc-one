SUMMARY = "AgenC ONE Firewall Rules"
DESCRIPTION = "nftables outbound-only firewall for AgenC ONE device"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c79ff39f19dfec6d293b95dea7b07891"

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
