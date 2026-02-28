FROM crops/poky:ubuntu-22.04

# Yocto build dependencies
USER root
RUN apt-get update && apt-get install -y \
    gawk wget git diffstat unzip texinfo gcc build-essential \
    chrpath socat cpio python3 python3-pip python3-pexpect \
    xz-utils debianutils iputils-ping python3-git python3-jinja2 \
    python3-subunit zstd liblz4-tool file locales libacl1 \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8

# Build user (Yocto refuses to run as root)
RUN useradd -m -s /bin/bash yocto
USER yocto
WORKDIR /home/yocto

# Clone Yocto layers
RUN git clone -b scarthgap git://git.yoctoproject.org/poky.git && \
    git clone -b scarthgap git://git.yoctoproject.org/meta-raspberrypi.git && \
    git clone -b scarthgap git://git.openembedded.org/meta-openembedded.git

COPY --chown=yocto:yocto entrypoint.sh /home/yocto/entrypoint.sh
RUN chmod +x /home/yocto/entrypoint.sh

ENTRYPOINT ["/home/yocto/entrypoint.sh"]
