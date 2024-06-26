Meta layers used specifically for the purpose for thesis

Dir structure:

```
meta-custom/
├── recipes-connectivity
│   ├── iproute2
│   │   ├── iproute2
│   │   │   └── 0001-libc-compat.h-add-musl-workaround.patch
│   │   └── iproute2_6.7.0.bb
│   └── linuxptp
│       ├── linuxptp
│       │   ├── 0001-include-string.h-for-strncpy.patch
│       │   ├── 0002-linuxptp-Use-CC-in-incdefs.sh.patch
│       │   └── systemd
│       │       ├── phc2sys@.service.in
│       │       └── ptp4l@.service.in
│       └── linuxptp_4.1.bb
├── recipes-kernel
│   ├── linux
│   │   ├── linux-rt
│   │   │   └── my_kernel
│   │   │       ├── 0001_ethtool_macsec.patch
│   │   │       ├── 0002_debug_ethtool.patch
│   │   │       └── 0003_crypto_kernel_reqs.patch
│   │   └── linux-rt.bbappend
│   └── wireguard
│       └── wireguard-tools_%.bbappend
└── recipes-support
    └── strongswan
        └── strongswan_5.9.13.bb
```

Sources: 

* iproute2: https://github.com/yoctoproject/poky/commit/2e07f1440f36d0efc304f1dbe8c1b577ce561460
* linuxptp: https://github.com/openembedded/meta-openembedded/commit/e12d38e91efff3f9f28fc35f9b9dc16557d5f849
* strongswan: https://github.com/openembedded/meta-openembedded/commit/5be2e20157f3025f9e2370933267a56fd526c58e
* macsec driver patch inspired by: https://elixir.bootlin.com/linux/v4.19.312/source/net/8021q/vlan_dev.c
