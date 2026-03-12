SUMMARY = "GoPoint for i.MX Application Processors"
DESCRIPTION = "Launcher for GoPoint for i.MX Application Processors"
LICENSE = "BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=8414149b19eabc57ab1350562aa605b1"

NXP_DEMO_SRC ?= "git://github.com/nxp-imx-support/nxp-demo-experience.git;protocol=https"
NXP_DEMO_BRANCH ?= "lf-6.6.36_2.1.0"
NXP_DEMO_SRCREV ?= "850269435708e4f177f36da017b2547fa97b0932"

PV = "${NXP_DEMO_BRANCH}+git${NXP_DEMO_SRCREV}"

SRC_URI = "${NXP_DEMO_SRC};branch=${NXP_DEMO_BRANCH};name=nxp-demo-experience"
SRCREV = "${NXP_DEMO_SRCREV}"

S = "${WORKDIR}/git"

inherit qt6-qmake

DEPENDS += " \
    qtbase \
    qtdeclarative \
    ncurses \
"

RDEPENDS:${PN}+= " qtbase \
    qtdeclarative \
    ncurses \
    qt5compat \
"

do_install() {
    install -d -m 755 ${D}${bindir}
    install ${B}/demoexperience ${D}${bindir}
    ln -sfr ${D}${bindir}/demoexperience ${D}${bindir}/gopoint

    install -d -m 755 ${D}${GPNT_APPS_FOLDER}
}

FILES:${PN} += "${bindir}/demoexperience ${bindir}/gopoint ${GPNT_APPS_FOLDER}"
