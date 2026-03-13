do_install:append:imx8mp-lpddr4-frdm() {
    install -d ${D}/Config
    install -d ${D}/mnt/openhd-boot

    # Remove prior full-partition mount rule (if present), then add folder bind mount rules.
    sed -i '/^[[:space:]]*LABEL=boot[[:space:]]\+\/Config[[:space:]]\+/d' ${D}${sysconfdir}/fstab

    if ! grep -q "^[[:space:]]*LABEL=boot[[:space:]]\\+/mnt/openhd-boot[[:space:]]" ${D}${sysconfdir}/fstab; then
        echo "LABEL=boot           /mnt/openhd-boot      vfat       defaults,nofail       0  0" >> ${D}${sysconfdir}/fstab
    fi

    if ! grep -q "^[[:space:]]*/mnt/openhd-boot/openhd[[:space:]]\\+/Config[[:space:]]" ${D}${sysconfdir}/fstab; then
        echo "/mnt/openhd-boot/openhd /Config            none       bind,nofail           0  0" >> ${D}${sysconfdir}/fstab
    fi
}

do_install:append() {
    if [ "${OPENHD_ENABLE_IW612}" != "1" ]; then
        install -d ${D}${sysconfdir}/modprobe.d
        cat > ${D}${sysconfdir}/modprobe.d/openhd-disable-nxp-wlan.conf << 'EOF'
# OpenHD default: disable NXP WLAN stack unless explicitly enabled.
blacklist mlan
blacklist moal
install mlan /bin/false
install moal /bin/false
EOF
    fi
}
