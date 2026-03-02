SUMMARY = "AgenC ONE Voice Task Operator"
DESCRIPTION = "Autonomous AI agent with voice-to-chain pipeline on Solana"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c84e74ca1e4a5830e4dc9e7a7e91cf9b"

SRC_URI = " \
    file://agenc_voice_task.py \
    file://agenc_voice.py \
    file://agenchi_display.py \
    file://requirements.txt \
    file://agenc-runtime.service \
"

RDEPENDS:${PN} = " \
    python3 \
    python3-pip \
    python3-pillow \
    python3-json \
    python3-asyncio \
    python3-websockets \
"

inherit systemd

SYSTEMD_SERVICE:${PN} = "agenc-runtime.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    # Agent runtime
    install -d ${D}/opt/agenc
    install -m 0755 ${WORKDIR}/agenc_voice_task.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/agenc_voice.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/agenchi_display.py ${D}/opt/agenc/
    install -m 0644 ${WORKDIR}/requirements.txt ${D}/opt/agenc/

    # systemd service
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/agenc-runtime.service ${D}${systemd_system_unitdir}/
}

FILES:${PN} = " \
    /opt/agenc/* \
    ${systemd_system_unitdir}/agenc-runtime.service \
"
