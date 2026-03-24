SUMMARY = "QOpenHD companion application"
DESCRIPTION = "Qt-based OpenHD ground-station companion application"
HOMEPAGE = "https://github.com/OpenHD/QOpenHD"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=1ccabeb20df52b9236fcc6ea3d7e6f55"

SRC_URI = "gitsm://github.com/OpenHD/QOpenHD.git;protocol=https;branch=2.7-evo"
SRCREV = "f67981240797b3cb278887ada07133e49dcf5dbb"

PV = "2.7-evo+git${SRCPV}"

S = "${WORKDIR}/git"
QMAKE_PROFILES = "${S}/QOpenHD.pro"

inherit qmake5_base pkgconfig

# QOpenHD's qmake project enables Qt TextToSpeech on Linux, but the current
# scarthgap meta-qt5 branch in this workspace does not provide a qtspeech recipe.
EXTRA_QMAKEVARS_PRE += "CONFIG-=EnableSpeech"

DEPENDS += " \
    ffmpeg \
    gstreamer1.0 \
    gstreamer1.0-plugins-base \
    libdrm \
    qtbase \
    qtcharts \
    qtdeclarative \
    qtlocation \
    qttools-native \
"

RDEPENDS:${PN} += " \
    ffmpeg \
    fontconfig \
    gstreamer1.0 \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libdrm \
    openhd-sys-utils \
    qtbase \
    qtcharts \
    qtdeclarative \
    qtlocation \
"

do_install() {
    install -d ${D}${bindir}
    install -d ${D}/usr/local/bin
    install -d ${D}/usr/local/share/qopenhd

    install -m 0755 ${B}/release/QOpenHD ${D}${bindir}/QOpenHD
    ln -sf ${bindir}/QOpenHD ${D}/usr/local/bin/QOpenHD

    install -m 0644 ${S}/rock_qt_eglfs_kms_config.json ${D}/usr/local/share/qopenhd/
    install -m 0644 ${S}/rpi_qt_eglfs_kms_config.json ${D}/usr/local/share/qopenhd/
}

FILES:${PN} += " \
    ${bindir}/QOpenHD \
    /usr/local/bin/QOpenHD \
    /usr/local/share/qopenhd \
    /usr/local/share/qopenhd/rock_qt_eglfs_kms_config.json \
    /usr/local/share/qopenhd/rpi_qt_eglfs_kms_config.json \
"
