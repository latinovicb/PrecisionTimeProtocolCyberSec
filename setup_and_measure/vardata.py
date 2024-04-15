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
REMOTE_DIR = "tmp"


# multiple pairs of masters/slaves can be done
ssh_conns = {
    "master": [SSHConn("192.168.88.101","root","",REMOTE_DIR),],
    "slave": [SSHConn("192.168.88.102","root","",REMOTE_DIR),],
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
CUSTOM_ID = f" -f /{REMOTE_DIR}/ptp_clock_id.cfg "
UNICAST_MASTER = f" -f /{REMOTE_DIR}/unicast_master.cfg "
UNICAST_SLAVE = f" -f /{REMOTE_DIR}/unicast_slave.cfg "
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
    ################################ SW_TIMESTAMPING ################################
    "no_enc_multicast_udp_sw": {
        "master": BASE + PHY_INTERFACE + L3 + SW,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE,
    },
    "no_enc_multicast_l2_sw": {
        "master": BASE + PHY_INTERFACE + L2 + SW,
        "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE,
    },

    "no_enc_unicast_udp_sw": {
        "master": BASE + PHY_INTERFACE + L3 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE,
    },
    "no_enc_unicast_l2_sw": {
        "master": BASE + PHY_INTERFACE + L2 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE,
    },

    # NOTE: wg tested only with multicast
    "wg_enc_multicast_udp_sw": {
        "master": BASE + WG_INTERFACE + L3 + SW + CUSTOM_ID,
        "slave": BASE + WG_INTERFACE + L3 + SW + SLAVE + CUSTOM_ID,
    },

    "wg_enc_multicast_l2_sw": {
        "master": BASE + WG_INTERFACE + L2 + SW + CUSTOM_ID,
        "slave": BASE + WG_INTERFACE + L2 + SW + SLAVE + CUSTOM_ID,
    },

    # NOTE: ipsec only with mulicast
    "ipsec_enc_unicast_udp_sw": {
        "master": BASE + PHY_INTERFACE + L3 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE,
    },

    # NOTE: not supported
    # "ipsec_enc_unicast_l2_sw": {
    #     "master": BASE + PHY_INTERFACE + L2 + SW + UNICAST_MASTER,
    #     "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE,
    # },

    "macsec_enc_multicast_udp_sw": {
        "master": BASE + MACSEC_INTERFACE + L3 + SW,
        "slave": BASE + MACSEC_INTERFACE + L3 + SW + SLAVE,
    },
    "macsec_enc_multicast_l2_sw": {
        "master": BASE + MACSEC_INTERFACE + L2 + SW,
        "slave": BASE + MACSEC_INTERFACE + L2 + SW + SLAVE,
    },

    "macsec_enc_unicast_udp_sw": {
        "master": BASE + MACSEC_INTERFACE + L3 + SW + UNICAST_MASTER,
        "slave": BASE + MACSEC_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE,
    },
    "macsec_enc_unicast_l2_sw": {
        "master": BASE + MACSEC_INTERFACE + L2 + SW + UNICAST_MASTER,
        "slave": BASE + MACSEC_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE,
    },

    ################################ HW_TIMESTAMPING  ################################
    "no_enc_multicast_udp_hw": {
        "master": BASE + PHY_INTERFACE + L3 + HW,
        "slave": BASE + PHY_INTERFACE + L3 + HW + SLAVE,
    },
    "no_enc_multicast_l2_hw": {
        "master": BASE + PHY_INTERFACE + L2 + HW,
        "slave": BASE + PHY_INTERFACE + L2 + HW + SLAVE,
    },

    # NOTE: not supported
    # "wg_enc_multicast_udp_hw": {
    #     "master": BASE + WG_INTERFACE + L3 + HW,
    #     "slave": BASE + WG_INTERFACE + L3 + HW + SLAVE,
    # },

    # NOTE: not supported
    # "wg_enc_multicast_l2_hw": {
    #     "master": BASE + WG_INTERFACE + L2 + HW,
    #     "slave": BASE + WG_INTERFACE + L2 + HW + SLAVE,
    # },
}

# endSection
