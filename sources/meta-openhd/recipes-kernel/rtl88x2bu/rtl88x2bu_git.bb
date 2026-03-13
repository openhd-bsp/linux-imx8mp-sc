SUMMARY = "Realtek RTL88x2BU WiFi driver"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b234ee4d69f5fce4486a80fdaf4a4263"

inherit module

SRC_URI = "gitsm://github.com/OpenHD/rtl88x2bu.git;branch=master;protocol=https"
SRCREV = "adf4b24eea2c5fa06a76f3239d509e2e787d1db8"

S = "${WORKDIR}/git"

DEPENDS += "virtual/kernel"

KERNEL_MODULE_AUTOLOAD += "88x2bu_ohd"

EXTRA_OEMAKE += "ARCH=arm64 CROSS_COMPILE=${TARGET_PREFIX} KSRC=${STAGING_KERNEL_BUILDDIR}"

do_configure:append() {
    sed -i 's/^CONFIG_PLATFORM_I386_PC *= *y/CONFIG_PLATFORM_I386_PC = n/' ${S}/Makefile
    sed -i 's/^CONFIG_PLATFORM_ARM64_RPI *= *n/CONFIG_PLATFORM_ARM64_RPI = y/' ${S}/Makefile
}

do_install() {
    install -d ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/kernel/drivers/net/wireless/
    install -m 0644 ${S}/88x2bu_ohd.ko ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/kernel/drivers/net/wireless/
}
