SUMMARY = "TCP / IP networking and traffic control utilities"
DESCRIPTION = "Iproute2 is a collection of utilities for controlling \
TCP / IP networking and traffic control in Linux.  Of the utilities ip \
and tc are the most important.  ip controls IPv4 and IPv6 \
configuration and tc stands for traffic control."
HOMEPAGE = "http://www.linuxfoundation.org/collaborate/workgroups/networking/iproute2"
SECTION = "base"
LICENSE = "GPL-2.0-or-later"
LIC_FILES_CHKSUM = "file://COPYING;md5=eb723b61539feef013de476e68b5c50a \
                    "

DEPENDS = "flex-native bison-native iptables libcap"

SRC_URI = "${KERNELORG_MIRROR}/linux/utils/net/${BPN}/${BP}.tar.xz \
           file://0001-libc-compat.h-add-musl-workaround.patch \
           "

SRC_URI[sha256sum] = "ff942dd9828d7d1f867f61fe72ce433078c31e5d8e4a78e20f02cb5892e8841d"

inherit update-alternatives bash-completion pkgconfig

PACKAGECONFIG ??= "tipc elf devlink"
PACKAGECONFIG[tipc] = ",,libmnl,"
PACKAGECONFIG[elf] = ",,elfutils,"
PACKAGECONFIG[devlink] = ",,libmnl,"
PACKAGECONFIG[rdma] = ",,libmnl,"
PACKAGECONFIG[selinux] = ",,libselinux"

IPROUTE2_MAKE_SUBDIRS = "lib tc ip bridge misc genl ${@bb.utils.filter('PACKAGECONFIG', 'devlink tipc rdma', d)}"

# CFLAGS are computed in Makefile and reference CCOPTS
#
EXTRA_OEMAKE = "\
    CC='${CC}' \
    KERNEL_INCLUDE=${STAGING_INCDIR} \
    DOCDIR=${docdir}/iproute2 \
    SUBDIRS='${IPROUTE2_MAKE_SUBDIRS}' \
    SBINDIR='${base_sbindir}' \
    CONF_USR_DIR='${libdir}/iproute2' \
    LIBDIR='${libdir}' \
    CCOPTS='${CFLAGS}' \
"

do_configure_append () {
    sh configure ${STAGING_INCDIR}
    # Explicitly disable ATM support
    sed -i -e '/TC_CONFIG_ATM/d' config.mk
}

do_install () {
    oe_runmake DESTDIR=${D} install
    mv ${D}${base_sbindir}/ip ${D}${base_sbindir}/ip.iproute2
    install -d ${D}${datadir}
    mv ${D}/share/* ${D}${datadir}/ || true
    rm ${D}/share -rf || true
}

# The .so files in iproute2-tc are modules, not traditional libraries
INSANE_SKIP_${PN}-tc = "dev-so"

IPROUTE2_PACKAGES =+ "\
    ${PN}-devlink \
    ${PN}-genl \
    ${PN}-ifstat \
    ${PN}-ip \
    ${PN}-lnstat \
    ${PN}-nstat \
    ${PN}-routel \
    ${PN}-rtacct \
    ${PN}-ss \
    ${PN}-tc \
    ${PN}-tipc \
    ${PN}-rdma \
"

PACKAGE_BEFORE_PN = "${IPROUTE2_PACKAGES}"
RDEPENDS_${PN} += "${PN}-ip"

FILES_${PN}-tc = "${base_sbindir}/tc* \
                  ${libdir}/tc/*.so"
FILES_${PN}-lnstat = "${base_sbindir}/lnstat \
                      ${base_sbindir}/ctstat \
                      ${base_sbindir}/rtstat"
FILES_${PN}-ifstat = "${base_sbindir}/ifstat"
FILES_${PN}-ip = "${base_sbindir}/ip.* ${libdir}/iproute2"
FILES_${PN}-genl = "${base_sbindir}/genl"
FILES_${PN}-rtacct = "${base_sbindir}/rtacct"
FILES_${PN}-nstat = "${base_sbindir}/nstat"
FILES_${PN}-ss = "${base_sbindir}/ss"
FILES_${PN}-tipc = "${base_sbindir}/tipc"
FILES_${PN}-devlink = "${base_sbindir}/devlink"
FILES_${PN}-rdma = "${base_sbindir}/rdma"
FILES_${PN}-routel = "${base_sbindir}/routel"

RDEPENDS_${PN}-routel = "python3-core"

ALTERNATIVE_${PN}-ip = "ip"
ALTERNATIVE_TARGET[ip] = "${base_sbindir}/ip.${BPN}"
ALTERNATIVE_LINK_NAME[ip] = "${base_sbindir}/ip"
ALTERNATIVE_PRIORITY = "100"

ALTERNATIVE_${PN}-tc = "tc"
ALTERNATIVE_LINK_NAME[tc] = "${base_sbindir}/tc"
ALTERNATIVE_PRIORITY_${PN}-tc = "100"
