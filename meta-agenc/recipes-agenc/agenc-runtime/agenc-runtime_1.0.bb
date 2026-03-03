SUMMARY = "AgenC ONE Agent Runtime"
DESCRIPTION = "Autonomous AI agent with voice-to-chain pipeline, CLI, display control, and boot splash"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c79ff39f19dfec6d293b95dea7b07891"

SRC_URI = " \
    file://agenc_voice_task.py \
    file://agenc_voice.py \
    file://WhisPlay.py \
    file://agenchi_display.py \
    file://agenc-cli.py \
    file://agenc-display.py \
    file://agenc-boot-splash.py \
    file://agenc-splash.py \
    file://login_centered.sh \
    file://DejaVuSans-Bold.ttf \
    file://requirements.txt \
    file://agenc-runtime.service \
    file://agenc-splash.service \
    file://agenc-boot-logo.service \
    file://boot_logo.png \
"

RDEPENDS:${PN} = " \
    python3 \
    python3-pip \
    python3-pillow \
    python3-json \
    python3-asyncio \
    python3-websockets \
    python3-spidev \
"

inherit systemd

SYSTEMD_SERVICE:${PN} = "agenc-runtime.service agenc-boot-logo.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    # Agent runtime scripts
    install -d ${D}/opt/agenc
    install -m 0755 ${WORKDIR}/agenc_voice_task.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/agenc_voice.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/WhisPlay.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/agenchi_display.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/requirements.txt ${D}/opt/agenc/

    # CLI agent
    install -m 0755 ${WORKDIR}/agenc-cli.py ${D}/opt/agenc/agenc-cli.py

    # Display control tool
    install -m 0755 ${WORKDIR}/agenc-display.py ${D}/opt/agenc/agenc-display.py

    # Boot splash (HDMI framebuffer)
    install -m 0755 ${WORKDIR}/agenc-boot-splash.py ${D}/opt/agenc/
    install -m 0755 ${WORKDIR}/agenc-splash.py ${D}/opt/agenc/

    # Login wrapper (centered cursor + boot logo trigger)
    install -m 0755 ${WORKDIR}/login_centered.sh ${D}/opt/agenc/

    # Font for display rendering
    install -m 0644 ${WORKDIR}/DejaVuSans-Bold.ttf ${D}/opt/agenc/

    # Boot logo
    install -m 0644 ${WORKDIR}/boot_logo.png ${D}/opt/agenc/

    # Symlinks for CLI commands
    install -d ${D}${bindir}
    ln -sf /opt/agenc/agenc-cli.py ${D}${bindir}/agenc
    ln -sf /opt/agenc/agenc-display.py ${D}${bindir}/agenc-display

    # systemd services
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/agenc-runtime.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${WORKDIR}/agenc-boot-logo.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${WORKDIR}/agenc-splash.service ${D}${systemd_system_unitdir}/

    # Getty override for centered login
    install -d ${D}${systemd_system_unitdir}/getty@tty1.service.d
    cat > ${D}${systemd_system_unitdir}/getty@tty1.service.d/override.conf << 'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o "-p -- \\u" --noclear --nohostname -l /opt/agenc/login_centered.sh - $TERM
EOF
    chmod 0644 ${D}${systemd_system_unitdir}/getty@tty1.service.d/override.conf
}

FILES:${PN} = " \
    /opt/agenc/* \
    ${bindir}/agenc \
    ${bindir}/agenc-display \
    ${systemd_system_unitdir}/agenc-runtime.service \
    ${systemd_system_unitdir}/agenc-boot-logo.service \
    ${systemd_system_unitdir}/agenc-splash.service \
    ${systemd_system_unitdir}/getty@tty1.service.d/override.conf \
"
