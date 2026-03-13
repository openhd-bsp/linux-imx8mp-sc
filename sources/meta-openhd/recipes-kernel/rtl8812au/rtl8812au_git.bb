SUMMARY = "Realtek RTL8812AU WiFi driver"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b234ee4d69f5fce4486a80fdaf4a4263"

inherit module

SRC_URI = "gitsm://github.com/OpenHD/rtl8812au.git;branch=v5.6.4.2;protocol=https"
SRCREV = "1eb904c19566a23596d92c5d0a713f7dbc2b0009"

S = "${WORKDIR}/git"

DEPENDS += "virtual/kernel"

KERNEL_MODULE_AUTOLOAD += "8812au_ohd"

EXTRA_OEMAKE += "ARCH=arm64 CROSS_COMPILE=${TARGET_PREFIX} KSRC=${STAGING_KERNEL_BUILDDIR}"

do_configure:append() {
    sed -i 's/^CONFIG_PLATFORM_I386_PC *= *y/CONFIG_PLATFORM_I386_PC = n/' ${S}/Makefile
    sed -i 's/^CONFIG_PLATFORM_ARM64_RPI *= *n/CONFIG_PLATFORM_ARM64_RPI = y/' ${S}/Makefile
}

do_install() {
    install -d ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/kernel/drivers/net/wireless/
    install -m 0644 ${S}/88XXau_ohd.ko ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/kernel/drivers/net/wireless/
}
