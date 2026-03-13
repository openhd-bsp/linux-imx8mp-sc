OPENHD_ENABLE_IW612 ?= "0"

IMAGE_INSTALL:append = " ${@oe.utils.conditional('OPENHD_ENABLE_IW612', '1', 'iw612-autoload kernel-module-nxp-wlan', '', d)}"
