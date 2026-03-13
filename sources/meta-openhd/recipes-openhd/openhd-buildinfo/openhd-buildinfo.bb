SUMMARY = "Generate boot partition build info file"
LICENSE = "CLOSED"

inherit deploy

S = "${WORKDIR}"

do_compile[noexec] = "1"
do_install[noexec] = "1"

do_deploy[nostamp] = "1"
do_deploy() {
    install -d ${DEPLOYDIR}
    date -u "+%Y-%m-%d %H:%M:%S UTC" > ${DEPLOYDIR}/config.txt
}

addtask deploy after do_compile before do_build
