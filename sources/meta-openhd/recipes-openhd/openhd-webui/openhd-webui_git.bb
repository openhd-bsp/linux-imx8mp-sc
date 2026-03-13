SUMMARY = "OpenHD Web user interface"
LICENSE = "Unlicense"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=d88e9e08385d2a17052dac348bde4bc1"

SRC_URI = "git://github.com/OpenHD/OpenHD-WebUI.git;protocol=https;branch=dev-release \
           file://openhd-web-ui-sys-utils-order.conf \
          "
SRCREV = "${AUTOREV}"
S = "${WORKDIR}/git"

inherit systemd

# Node is required by the WebUI client build (ESProj)
DEPENDS += "nodejs-native"

# Allow internet during do_compile for dotnet + npm restore
do_compile[network] = "1"

# Runtime Identifier map
python __anonymous() {
    arch = d.getVar("TARGET_ARCH")
    rid = {
        "aarch64": "linux-arm64",
        "armv7a": "linux-arm",
        "x86_64": "linux-x64"
    }.get(arch)

    if not rid:
        bb.fatal("Unsupported arch '%s' for DOTNET_TARGET" % arch)

    d.setVar("DOTNET_TARGET", rid)
}

# Use dotnet from Yocto hosttools / SDK
DOTNET_NATIVE ?= "${@bb.utils.which(d.getVar('PATH'), 'dotnet')}"

do_compile() {
    if [ -z "${DOTNET_NATIVE}" ]; then
        bbfatal "dotnet not found in Yocto do_compile PATH"
    fi

    # Ensure native tools (node) are visible
    export PATH="${STAGING_BINDIR_NATIVE}:${PATH}"

    if ! command -v node >/dev/null 2>&1; then
        bbfatal "node not found in Yocto do_compile PATH (expected via nodejs-native)"
    fi

    ${DOTNET_NATIVE} publish \
        -c Release \
        -r ${DOTNET_TARGET} \
        --self-contained \
        -o ${B}/publish \
        src/OpenHdWebUi.Server/OpenHdWebUi.Server.csproj
}

do_install() {
    install -d ${D}/usr/local/share/openhd/web-ui
    cp -r ${B}/publish/* ${D}/usr/local/share/openhd/web-ui/

    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${S}/openhd-web-ui.service ${D}${systemd_unitdir}/system/

    install -d ${D}${systemd_unitdir}/system/openhd-web-ui.service.d
    install -m 0644 ${WORKDIR}/openhd-web-ui-sys-utils-order.conf \
        ${D}${systemd_unitdir}/system/openhd-web-ui.service.d/10-sys-utils-order.conf
}

# Runtime dependencies
RDEPENDS:${PN} += "zlib openhd-sys-utils"

# Suppress QA noise for self-contained dotnet output
INSANE_SKIP:${PN} += "libdir buildpaths file-rdeps"

# Systemd integration
SYSTEMD_SERVICE:${PN} = "openhd-web-ui.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

FILES:${PN} += " \
    /usr/local/share/openhd/web-ui/ \
    ${systemd_unitdir}/system/openhd-web-ui.service \
    ${systemd_unitdir}/system/openhd-web-ui.service.d/10-sys-utils-order.conf \
"
