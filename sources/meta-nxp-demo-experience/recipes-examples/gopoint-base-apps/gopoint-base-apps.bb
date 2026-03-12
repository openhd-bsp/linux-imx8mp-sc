SUMMARY = "GoPoint for i.MX Application Processors"
DESCRIPTION = "Launcher for GoPoint for i.MX Application Processors"
LICENSE = "BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=8414149b19eabc57ab1350562aa605b1"

S = "${WORKDIR}/git"

SRCBRANCH = "lf-6.6.36_2.1.0"

NXP_DEMO_LIST_SRC ?= "git://github.com/nxp-imx-support/nxp-demo-experience-demos-list.git;protocol=https"

SRC_URI = "${NXP_DEMO_LIST_SRC};branch=${SRCBRANCH};name=demos"

SRCREV = "5570a8cf588ae9752ed38607bb4fe35da183567d"

PV = "lf-6.6.36_2.1.0+git${SRCREV}"

RDEPENDS:${PN} += "bash python3-packaging python3-paramiko iproute2 iproute2-tc python3-matplotlib "

do_install() {
    install -d -m 755 ${D}${GPNT_APPS_FOLDER}
    cp -r ${WORKDIR}/git/* ${D}${GPNT_APPS_FOLDER}
}

FILES:${PN} += "${GPNT_APPS_FOLDER}/* "