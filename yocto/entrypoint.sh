#!/bin/bash
set -e

cd /home/yocto

# Source Yocto build environment
source poky/oe-init-build-env build

# Add layers if not already added
bitbake-layers show-layers 2>/dev/null | grep -q meta-raspberrypi || \
    bitbake-layers add-layer /home/yocto/meta-raspberrypi
bitbake-layers show-layers 2>/dev/null | grep -q meta-oe || \
    bitbake-layers add-layer /home/yocto/meta-openembedded/meta-oe
bitbake-layers show-layers 2>/dev/null | grep -q meta-python || \
    bitbake-layers add-layer /home/yocto/meta-openembedded/meta-python
bitbake-layers show-layers 2>/dev/null | grep -q meta-networking || \
    bitbake-layers add-layer /home/yocto/meta-openembedded/meta-networking
bitbake-layers show-layers 2>/dev/null | grep -q meta-agenc || \
    bitbake-layers add-layer /home/yocto/meta-agenc

# Set machine
grep -q 'MACHINE.*agenc-one' conf/local.conf || \
    echo 'MACHINE = "agenc-one"' >> conf/local.conf

# Execute command or default to build
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    bitbake agenc-os-image
fi
