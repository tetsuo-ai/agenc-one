# AgenC OS: U-Boot configuration for A/B boot and RAUC integration

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += "file://boot.cmd"

# Enable verified boot support
UBOOT_ENV = "boot"
UBOOT_ENV_SUFFIX = "scr"

do_compile:append() {
    mkimage -C none -A arm64 -T script -d ${WORKDIR}/boot.cmd ${WORKDIR}/boot.scr
}

do_deploy:append() {
    install -m 0644 ${WORKDIR}/boot.scr ${DEPLOYDIR}/
}
