# AgenC OS A/B Boot Script
# RAUC manages the BOOT_ORDER and BOOT_x_LEFT variables

test -n "${BOOT_ORDER}" || setenv BOOT_ORDER "A B"
test -n "${BOOT_A_LEFT}" || setenv BOOT_A_LEFT 3
test -n "${BOOT_B_LEFT}" || setenv BOOT_B_LEFT 3

setenv bootargs "console=ttyS0,115200 root=PARTLABEL=rootfs-a rootfstype=ext4 rootwait ro quiet"

for BOOT_SLOT in ${BOOT_ORDER}; do
    if test "x${BOOT_SLOT}" = "xA"; then
        if test ${BOOT_A_LEFT} -gt 0; then
            setexpr BOOT_A_LEFT ${BOOT_A_LEFT} - 1
            setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p2 rootfstype=ext4 rootwait ro quiet rauc.slot=A"
            saveenv
            echo "Booting slot A (${BOOT_A_LEFT} attempts left)"
            load mmc 0:1 ${kernel_addr_r} Image
            load mmc 0:1 ${fdt_addr_r} bcm2710-rpi-zero-2-w.dtb
            booti ${kernel_addr_r} - ${fdt_addr_r}
        fi
    elif test "x${BOOT_SLOT}" = "xB"; then
        if test ${BOOT_B_LEFT} -gt 0; then
            setexpr BOOT_B_LEFT ${BOOT_B_LEFT} - 1
            setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p3 rootfstype=ext4 rootwait ro quiet rauc.slot=B"
            saveenv
            echo "Booting slot B (${BOOT_B_LEFT} attempts left)"
            load mmc 0:1 ${kernel_addr_r} Image
            load mmc 0:1 ${fdt_addr_r} bcm2710-rpi-zero-2-w.dtb
            booti ${kernel_addr_r} - ${fdt_addr_r}
        fi
    fi
done

echo "No bootable slot found! Starting recovery..."
reset
