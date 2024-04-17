Meta layers used specifically for the purpose for thesis

Dir structure:

```
├── custom_layers
│   ├── recipes-connectivity
│   │   ├── iproute2
│   │   │   ├── iproute2
│   │   │   │   └── 0001-libc-compat.h-add-musl-workaround.patch
│   │   │   └── iproute2_6.7.0.bb
│   │   └── linuxptp
│   │       ├── linuxptp
│   │       │   ├── 0001-include-string.h-for-strncpy.patch
│   │       │   ├── 0002-linuxptp-Use-CC-in-incdefs.sh.patch
│   │       │   └── systemd
│   │       │       ├── phc2sys@.service.in
│   │       │       └── ptp4l@.service.in
│   │       └── linuxptp_4.1.bb
│   ├── recipes-kernel
│   │   ├── linux
│   │   │   └── linux-rt
│   │   │       └── my_kernel
│   │   │           ├── 0001_ethtool_macsec.patch
│   │   │           ├── 0002_debug_ethtool.patch
│   │   │           └── 0003_crypto_kernel_reqs.patch # change diff path lines here
│   │   └── wireguard
│   │       └── wireguard-tools_%.bbappend
│   └── recipes-support
│       └── strongswan
│           └── strongswan_5.9.13.bb
└── README.md
```

Sources: 

* iproute2: https://git.yoctoproject.org/poky/tree/meta/recipes-connectivity/iproute2/iproute2_6.7.0.bb
    * commit_sha: 8c460adf731db2d699c523d0017644cc7162efe9
* linuxptp: https://github.com/openembedded/meta-openembedded/tree/master/meta-oe/recipes-connectivity/linuxptp/linuxptp
    * commit_sha: e12d38e91efff3f9f28fc35f9b9dc16557d5f849
* strongswan: https://github.com/openembedded/meta-openembedded/tree/master/meta-networking/recipes-support/strongswan
    * commit_sha: 5be2e20157f3025f9e2370933267a56fd526c58e 

