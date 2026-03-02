# AgenC OS: Additional volatile binds for read-only rootfs
# These directories are bind-mounted from tmpfs at boot

VOLATILE_BINDS:append = "\n/tmp /var/tmp\n/tmp /var/cache\n/tmp /var/lib/systemd\n/data/agenc/logs /var/log"
