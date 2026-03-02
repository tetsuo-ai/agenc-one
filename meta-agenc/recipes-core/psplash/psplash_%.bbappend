# AgenC OS: Custom boot splash with AGENC logo
# White geometric logo on black background

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SPLASH_IMAGES = "file://agenc-splash.png;outsuffix=default"

# Black background, no progress bar animation
EXTRA_OECONF += "--disable-startup-msg"
