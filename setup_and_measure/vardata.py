from dataclasses import dataclass


@dataclass
class SSHConn:
    addr: str
    user: str
    passw: str
    dir: str


@dataclass
class PlotLogConf:
    time: int  # in s
    buff_size: int  # after how many messages new image is generated (by default 1 seconds - 1 message)
    location: str  # location on where the plots and plots and data will be saved on this pc


@dataclass
class Ptp4lDataLogs:
    log_data: dict  # log data provided by ptp4l
    re_pattern: int  # regex pattern created specifically to match the values from above specified data


# Section 1
PHY_INTERFACE = " eth1 "
WG_INTERFACE = " wg0 "
MACSEC_INTERFACE = " macsec0 "


# multiple pairs of masters/slaves can be done
ssh_conns = {
    "master": [SSHConn("192.168.88.101","root","","tmp"),],
    "slave": [SSHConn("192.168.88.102","root","","tmp"),],
}

ptp_log_config = PlotLogConf(60,10,"/tmp/ptp_reads")

# endSection

# Section 2
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
CUSTOM_ID = " -f ptp_clock_id.cfg "
UNICAST_MASTER = " -f unicast_master.cfg "
UNICAST_SLAVE = " -f unicast_slave.cfg "
BASE = "ptp4l -m -i "  # this will be used always -- the following argument is interface

# Interfaces used for setup & measurment
ptp_sec_cons = {
    PHY_INTERFACE.strip(): "192.0.2.",
    WG_INTERFACE.strip(): "198.51.100.",
    MACSEC_INTERFACE.strip(): "203.0.113.",
}

# currently only these data logs supported
ptp4l_log_match = Ptp4lDataLogs(
    {
        "ptp4l_runtime": "s",  # ptp4l_runtime used just for log consitecny verification
        "master_offset": "ns",
        "servo_freq": "ppb",
        "path_delay": "ns",
    },
    r"(?:\b[+\-]?\d+(?:\.\d+)?\b\s*(?![-+])|[+\-])"
)

netmask = "/24"  # this netmask will be assumed for everything

ptp_sec_cmds = {
    "no_enc_multicast_udp_sw": {
        "master": BASE + PHY_INTERFACE + L3 + SW,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE,
    },
    "no_enc_multicast_l2_sw": {
        "master": BASE + PHY_INTERFACE + L2 + SW,
        "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE,
    },

    "no_enc_multicast_udp_hw": {
        "master": BASE + PHY_INTERFACE + L3 + HW,
        "slave": BASE + PHY_INTERFACE + L3 + HW + SLAVE,
    },
    "no_enc_multicast_l2_hw": {
        "master": BASE + PHY_INTERFACE + L2 + HW,
        "slave": BASE + PHY_INTERFACE + L2 + HW + SLAVE,
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

# endSection
