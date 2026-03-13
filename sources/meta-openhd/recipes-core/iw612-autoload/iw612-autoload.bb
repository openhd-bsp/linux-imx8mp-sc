SUMMARY = "Autoload NXP IW612 Wi-Fi modules at boot"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://iw612.conf"

S = "${WORKDIR}"

do_install() {
	install -d ${D}${sysconfdir}/modules-load.d
	install -m 0644 ${WORKDIR}/iw612.conf ${D}${sysconfdir}/modules-load.d/iw612.conf
}

FILES:${PN} += "${sysconfdir}/modules-load.d/iw612.conf"
