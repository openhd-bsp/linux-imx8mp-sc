SUMMARY = "OpenHD: Open-source digital video transmission system"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://../LICENSE;md5=1ebbd3e34237af26da5dc08a4e440464"



SRC_URI = "gitsm://github.com/openhd/OpenHD.git;protocol=https;branch=dev-release \
           file://openhd_mod-sys-utils-order.conf \
          "

SRCREV = "${AUTOREV}"

# Give packages a monotonic version so apt/opkg prefers newer commits.
PV = "1.0+git${SRCPV}"

S = "${WORKDIR}/git/OpenHD"

inherit cmake pkgconfig systemd

DEPENDS = "flac poco libsodium gstreamer1.0 gstreamer1.0-plugins-base libpcap libusb1 libv4l"

RDEPENDS:${PN} += " \
  gstreamer1.0 \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  v4l-utils \
  openhd-webui \
  openhd-sys-utils \
"

SYSTEMD_SERVICE:${PN} = "openhd_mod.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install:append() {
    # Install systemd service
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${S}/../systemd/openhd_mod.service ${D}${systemd_unitdir}/system

    # Create required directories and files
    install -d ${D}/Video
    install -d ${D}/boot/openhd
    install -d ${D}/usr/local/share/openhd/
    touch ${D}/usr/local/share/openhd/licence
    touch ${D}/boot/openhd/air.txt

    # Ensure all OpenHD service variants wait for openhd-sys-utils.
    install -d ${D}${systemd_unitdir}/system/openhd.service.d
    install -m 0644 ${WORKDIR}/openhd_mod-sys-utils-order.conf \
        ${D}${systemd_unitdir}/system/openhd.service.d/10-sys-utils-order.conf

    install -d ${D}${systemd_unitdir}/system/openhd_mod.service.d
    install -m 0644 ${WORKDIR}/openhd_mod-sys-utils-order.conf \
        ${D}${systemd_unitdir}/system/openhd_mod.service.d/10-sys-utils-order.conf

    install -d ${D}${systemd_unitdir}/system/openhd_rpi.service.d
    install -m 0644 ${WORKDIR}/openhd_mod-sys-utils-order.conf \
        ${D}${systemd_unitdir}/system/openhd_rpi.service.d/10-sys-utils-order.conf

    install -d ${D}${systemd_unitdir}/system/openhd-x20.service.d
    install -m 0644 ${WORKDIR}/openhd_mod-sys-utils-order.conf \
        ${D}${systemd_unitdir}/system/openhd-x20.service.d/10-sys-utils-order.conf
}

FILES:${PN} += " \
    ${bindir}/* \
    ${systemd_unitdir}/system/openhd.service \
    ${systemd_unitdir}/system/openhd.service.d/10-sys-utils-order.conf \
    ${systemd_unitdir}/system/openhd_mod.service.d/10-sys-utils-order.conf \
    ${systemd_unitdir}/system/openhd_rpi.service.d/10-sys-utils-order.conf \
    ${systemd_unitdir}/system/openhd-x20.service.d/10-sys-utils-order.conf \
    /Video \
    /boot/openhd \
    /boot/openhd/air.txt \
    /usr/local \
    /usr/local/share \
    /usr/local/share/openhd \
    /usr/local/share/openhd/licence \
"
