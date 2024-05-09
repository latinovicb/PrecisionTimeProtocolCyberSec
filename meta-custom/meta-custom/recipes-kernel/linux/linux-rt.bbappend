FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI_append_my-linux = " \
        file://0001_ethtool_macsec.patch \
        file://0002_debug_ethtool.patch \
        file://0003_crypto_kernel_reqs.patch \
"
