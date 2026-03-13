FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " file://start_isp.sh"

do_install:append() {
    # Override vendor script with project-maintained version.
    install -m 0755 ${WORKDIR}/start_isp.sh ${D}/opt/imx8-isp/bin/start_isp.sh
}
