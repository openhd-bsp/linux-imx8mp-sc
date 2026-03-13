SUMMARY = "Realtek RTL88x2CU WiFi driver"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=1ebbd3e34237af26da5dc08a4e440464"

inherit module

SRC_URI = "gitsm://github.com/OpenHD/rtl88x2cu.git;branch=master;protocol=https"
SRCREV = "a29f71d2d7a3dae5ab5f2b09dcaa94d8ba8846da"

S = "${WORKDIR}/git"

DEPENDS += "virtual/kernel"

KERNEL_MODULE_AUTOLOAD += "88x2cu_ohd"

EXTRA_OEMAKE += "ARCH=arm64 CROSS_COMPILE=${TARGET_PREFIX} KSRC=${STAGING_KERNEL_BUILDDIR}"

do_configure:append() {
    sed -i 's/^CONFIG_PLATFORM_I386_PC *= *y/CONFIG_PLATFORM_I386_PC = n/' ${S}/Makefile
    sed -i 's/^CONFIG_PLATFORM_ARM64_RPI *= *n/CONFIG_PLATFORM_ARM64_RPI = y/' ${S}/Makefile
}

do_install() {
    install -d ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/kernel/drivers/net/wireless/
    install -m 0644 ${S}/88x2cu_ohd.ko ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/kernel/drivers/net/wireless/
}
