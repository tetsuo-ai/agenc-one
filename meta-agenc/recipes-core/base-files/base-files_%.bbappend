# AgenC OS: /data mount point and fstab entries for read-only rootfs

do_install:append() {
    # Create mount points
    install -d ${D}/data

    # Add /data partition to fstab
    echo "/dev/mmcblk0p4  /data  ext4  defaults,noatime  0  2" >> ${D}${sysconfdir}/fstab

    # tmpfs mounts for volatile state
    echo "tmpfs  /tmp   tmpfs  defaults,nosuid,nodev,size=32M  0  0" >> ${D}${sysconfdir}/fstab
    echo "tmpfs  /run   tmpfs  defaults,nosuid,nodev,mode=755,size=16M  0  0" >> ${D}${sysconfdir}/fstab
}
