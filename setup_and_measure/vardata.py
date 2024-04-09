# SSH connection for setup

PHY_INTERFACE = " eth1 "
WG_INTERFACE = " wg0 "
MACSEC_INTERFACE = " macsec0 "

HW = " -H "
SW = " -S "

E2E = " -E "
P2P = " -P "
AUTO = " -A "
L2 = " -2 "
L3 = " -4 "  # ipv4 only
HW = " -H "
SW = " -S "
SLAVE = " -s "

BASE = (
    "ptp4l -m -i "  # this will be used always -- first following argument is interface
)

ssh_conns = {
    "master": ["192.168.88.101"],
    "slave": ["192.168.88.102"],
}

# Interfaces used for setup & measurment
ptp_sec_cons = {
    PHY_INTERFACE.strip(): "192.0.2.",
    WG_INTERFACE.strip(): "198.51.100.",
    MACSEC_INTERFACE.strip(): "203.0.113.",
}

ptp_sec_cmds = {
    "no_enc_multicast_udp_hw": {
        "master": BASE + PHY_INTERFACE + L3 + HW,
        "slave": BASE + PHY_INTERFACE + L3 + HW + SLAVE,
    },
    "no_enc_multicast_udp_sw": {
        "master": BASE + PHY_INTERFACE + L3 + SW,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE,
    },
    "no_enc_multicast_l2_hw": {
        "master": BASE + PHY_INTERFACE + L2 + HW,
        "slave": BASE + PHY_INTERFACE + L2 + HW + SLAVE,
    },
    "no_enc_multicast_l2_sw": {
        "master": BASE + PHY_INTERFACE + L2 + SW,
        "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE,
    },
    # "no_enc_unicast_udp_hw": {
    #     "master": "ptp4l -m -f settings.cfg -i" + PHY_INTERFACE,
    #     "slave": "ptp4l -m -i eth1 -f settings.cfg -s",
    # },
    # "no_enc_unicast_udp_sw": {
    #     "master": "ptp4l -m -i eth1 -l 7 -f settings.cfg",
    #     "slave": "ptp4l -m -i eth1 -f settings.cfg -s",
    # },
}
