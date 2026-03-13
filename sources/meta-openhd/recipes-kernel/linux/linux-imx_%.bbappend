FILESEXTRAPATHS:prepend := "${THISDIR}/linux-imx:"

OPENHD_ENABLE_IW612 ?= "0"

SRC_URI:append = "${@oe.utils.conditional('OPENHD_ENABLE_IW612', '1', ' file://os08a20-wlan.config', '', d)}"
DELTA_KERNEL_DEFCONFIG:append = "${@oe.utils.conditional('OPENHD_ENABLE_IW612', '1', ' os08a20-wlan.config', '', d)}"
