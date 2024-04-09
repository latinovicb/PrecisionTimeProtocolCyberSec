from dataclasses import dataclass

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
    "ptp4l -m -i "  # this will be used always -- the following argument is interface
)


@dataclass
class SSHConn:
    addr: str
    user: str
    passw: str
    dir: str


# multiple paris of masters -- slaves can be done
ssh_conns = {
    "master": [SSHConn("192.168.88.101","root","","tmp"),],
    "slave": [SSHConn("192.168.88.102","root","","tmp"),],
}

ptp_log_config = {
    'timer': 300,  # in s
    'buff_size': 30,  # after how many ptp4l log lines new image is generated (log every one 1s)
    'location': "/tmp",  # location on where the plots and plots and data will be saved on this pc
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
    # "wg_enc_multicast_udp_hw": { # NOTE: not supported
    #     "master": BASE + WG_INTERFACE + L3 + HW,
    #     "slave": BASE + WG_INTERFACE + L3 + HW + SLAVE,
    # },
    # "wg_enc_multicast_udp_sw": {
    #     "master": BASE + WG_INTERFACE + L3 + SW,
    #     "slave": BASE + WG_INTERFACE + L3 + SW + SLAVE,
    # },
    # "wg_enc_multicast_l2_hw": { # NOTE: not supported
    #     "master": BASE + WG_INTERFACE + L2 + HW,
    #     "slave": BASE + WG_INTERFACE + L2 + HW + SLAVE,
    # },
    # "wg_enc_multicast_l2_sw": {
    #     "master": BASE + WG_INTERFACE + L2 + SW,
    #     "slave": BASE + WG_INTERFACE + L2 + SW + SLAVE,
    # },

    # TODO: figure out settings files
    # "no_enc_unicast_udp_hw": {
    #     "master": "ptp4l -m -f settings.cfg -i" + PHY_INTERFACE,
    #     "slave": "ptp4l -m -i eth1 -f settings.cfg -s",
    # },
    # "no_enc_unicast_udp_sw": {
    #     "master": "ptp4l -m -i eth1 -l 7 -f settings.cfg",
    #     "slave": "ptp4l -m -i eth1 -f settings.cfg -s",
    # },
}
