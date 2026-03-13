SUMMARY = "OpenHD system utilities orchestrator"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://inc/sysutil_settings.h;beginline=1;endline=22;md5=8eebd1796078e15c673ca7f63d41a47c"

SRC_URI = "git://github.com/OpenHD/OpenHD-SysUtils.git;protocol=https;branch=dev-release \
           file://0001-sysutil_wifi-fix-ambiguous-refresh_wifi_info-call.patch \
           file://0002-openhd-sys-utils-service-use-safe-boot-order.patch \
          "
SRCREV = "${AUTOREV}"

PV = "1.0+git${SRCPV}"
S = "${WORKDIR}/git"

inherit cmake systemd

do_configure:prepend() {
    # Upstream falls back to "c++" for host-side generator builds.
    # Yocto hosttools guarantees g++, not c++.
    export HOST_CXX="g++"
}

do_install:append() {
    # Upstream installs the unit to /lib/systemd/system.
    # Place it under Yocto's systemd_unitdir so systemd.bbclass can detect it.
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${S}/systemd/openhd-sys-utils.service ${D}${systemd_unitdir}/system/
    rm -f ${D}/lib/systemd/system/openhd-sys-utils.service
    rmdir --ignore-fail-on-non-empty ${D}/lib/systemd/system ${D}/lib/systemd ${D}/lib || true
}

SYSTEMD_SERVICE:${PN} = "openhd-sys-utils.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

FILES:${PN} += " \
    /usr/local/bin/openhd_sys_utils \
    ${systemd_unitdir}/system/openhd-sys-utils.service \
"
