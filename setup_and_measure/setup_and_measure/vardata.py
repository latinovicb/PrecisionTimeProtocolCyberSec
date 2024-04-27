from dataclasses import dataclass
import yaml

"""
INITIALIZATION
"""
@dataclass
class SSHConn:
    addr: str
    user: str
    passw: str
    dir: str


@dataclass
class PlotLogConf:
    time: int  # in s
    buff_size: int  # after how many ptp logs/messages new image is generated (by default 1 logs - 1 message)
    location: str  # location to where the plots and plots and data will be saved on this pc


@dataclass
class Ptp4lDataLogs:
    log_data: dict  # log data provided by ptp4l
    re_pattern: int  # regex pattern created specifically to match the values from above specified data


with open('confdata.yml', 'r') as file:
    config_data = yaml.safe_load(file)

"""
USER_DATA
"""
PHY_INTERFACE = f" {config_data['interfaces']['physical']} "
WG_INTERFACE = f" {config_data['interfaces']['wireguard']} "
MACSEC_INTERFACE = f" {config_data['interfaces']['macsec']} "
REMOTE_DIR = config_data['remote_directory']


# Multiple pairs of slaves & masters can be measured
ssh_conns = {
    "master": [SSHConn(config_data['ssh_conns']['master']['ip'],
                       config_data['ssh_conns']['master']['username'],
                       config_data['ssh_conns']['master']['password'], REMOTE_DIR)],
    "slave": [SSHConn(config_data['ssh_conns']['slave']['ip'],
                      config_data['ssh_conns']['slave']['username'],
                      config_data['ssh_conns']['slave']['password'], REMOTE_DIR)],
}

ptp_log_config = PlotLogConf(config_data['ptp_log_configuration']['measurment_time'],
                             config_data['ptp_log_configuration']['buff_size'],
                             config_data['ptp_log_configuration']['log_directory'],
                             )


"""
MEASURMENT_SPECS
"""
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
UNICAST_SLAVE = f" -f /{REMOTE_DIR}/unicast_slave_{PHY_INTERFACE.strip()}.cfg "
UNICAST_SLAVE_WG = f" -f /{REMOTE_DIR}/unicast_slave_{WG_INTERFACE.strip()}.cfg "
UNICAST_SLAVE_MAC = f" -f /{REMOTE_DIR}/unicast_slave_{MACSEC_INTERFACE.strip()}.cfg "
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
        "servo": "state",
    },
    r"(?:\b[+\-]?\d+(?:\.\d+)?\b\s*(?![-+])|[+\-]|s\d+)"
)

netmask = "/24"  # this netmask will be assumed for everything

ptp_sec_cmds = {

    # SW_TIMESTAMPING

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

    "wg_enc_multicast_udp_sw": {
        "master": BASE + WG_INTERFACE + L3 + SW + CUSTOM_ID,
        "slave": BASE + WG_INTERFACE + L3 + SW + SLAVE + CUSTOM_ID,
    },

    "wg_enc_multicast_l2_sw": {  # NOTE: does not work -- tun interface has no mac
        "master": BASE + WG_INTERFACE + L2 + SW + CUSTOM_ID,
        "slave": BASE + WG_INTERFACE + L2 + SW + SLAVE + CUSTOM_ID,
    },

    "wg_enc_unicast_udp_sw": {
        "master": BASE + WG_INTERFACE + L3 + SW + UNICAST_MASTER,
        "slave": BASE + WG_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE_WG,
    },

    "wg_enc_unicast_l2_sw": {   # NOTE: does not work -- tun interface has no mac
        "master": BASE + WG_INTERFACE + L2 + SW + UNICAST_MASTER,
        "slave": BASE + WG_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE_WG,
    },

    "ipsec_enc_unicast_udp_sw_tunnel": {
        "master": BASE + PHY_INTERFACE + L3 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE,
    },

    "ipsec_enc_unicast_l2_sw_tunnel": {
        "master": BASE + PHY_INTERFACE + L2 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE,
    },

    "ipsec_enc_unicast_udp_sw_transport": {
        "master": BASE + PHY_INTERFACE + L3 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE,
    },

    "ipsec_enc_unicast_l2_sw_transport": {
        "master": BASE + PHY_INTERFACE + L2 + SW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE,
    },

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
        "slave": BASE + MACSEC_INTERFACE + L3 + SW + SLAVE + UNICAST_SLAVE_MAC,
    },
    "macsec_enc_unicast_l2_sw": {
        "master": BASE + MACSEC_INTERFACE + L2 + SW + UNICAST_MASTER,
        "slave": BASE + MACSEC_INTERFACE + L2 + SW + SLAVE + UNICAST_SLAVE_MAC,
    },

    # HW_TIMESTAMPING

    "no_enc_multicast_udp_hw": {
        "master": BASE + PHY_INTERFACE + L3 + HW,
        "slave": BASE + PHY_INTERFACE + L3 + HW + SLAVE,
    },
    "no_enc_multicast_l2_hw": {
        "master": BASE + PHY_INTERFACE + L2 + HW,
        "slave": BASE + PHY_INTERFACE + L2 + HW + SLAVE,
    },

    "no_enc_unicast_udp_hw": {
        "master": BASE + PHY_INTERFACE + L3 + HW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + HW + UNICAST_SLAVE,
    },

    "no_enc_unicast_l2_hw": {
        "master": BASE + PHY_INTERFACE + L2 + HW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L2 + HW + UNICAST_SLAVE,
    },

    # NOTE: not supported -- wg tun interface cannnot hardware timestamp
    # "wg_enc_multicast_udp_hw": {
    #     "master": BASE + WG_INTERFACE + L3 + HW,
    #     "slave": BASE + WG_INTERFACE + L3 + HW + SLAVE,
    # },

    # NOTE: not supported -- wg tun interface cannnot hardware timestamp
    # "wg_enc_multicast_l2_hw": {
    #     "master": BASE + WG_INTERFACE + L2 + HW,
    #     "slave": BASE + WG_INTERFACE + L2 + HW + SLAVE,
    # },

    # NOTE: ipsec does not support multicast
    "ipsec_enc_unicast_udp_hw_tunnel": {
        "master": BASE + PHY_INTERFACE + L3 + HW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + HW + SLAVE + UNICAST_SLAVE,
    },

    # NOTE: not supported -- unicast is based on ipv4 address communication - so it won't work with l2 transport
    "ipsec_enc_unicast_l2_hw_tunnel": {
        "master": BASE + PHY_INTERFACE + L2 + HW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L2 + HW + SLAVE + UNICAST_SLAVE,
    },

    "ipsec_enc_unicast_udp_hw_transport": {
        "master": BASE + PHY_INTERFACE + L3 + HW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L3 + HW + SLAVE + UNICAST_SLAVE,
    },

    "ipsec_enc_unicast_l2_hw_transport": {
        "master": BASE + PHY_INTERFACE + L2 + HW + UNICAST_MASTER,
        "slave": BASE + PHY_INTERFACE + L2 + HW + SLAVE + UNICAST_SLAVE,
    },

    "macsec_enc_multicast_udp_hw": {
        "master": BASE + MACSEC_INTERFACE + L3 + HW,
        "slave": BASE + MACSEC_INTERFACE + L3 + HW + SLAVE,
    },
    "macsec_enc_multicast_l2_hw": {
        "master": BASE + MACSEC_INTERFACE + L2 + HW,
        "slave": BASE + MACSEC_INTERFACE + L2 + HW + SLAVE,
    },

    "macsec_enc_unicast_udp_hw": {
        "master": BASE + MACSEC_INTERFACE + L3 + HW + UNICAST_MASTER,
        "slave": BASE + MACSEC_INTERFACE + L3 + HW + SLAVE + UNICAST_SLAVE_MAC,
    },
    "macsec_enc_unicast_l2_hw": {
        "master": BASE + MACSEC_INTERFACE + L2 + HW + UNICAST_MASTER,
        "slave": BASE + MACSEC_INTERFACE + L2 + HW + SLAVE + UNICAST_SLAVE_MAC,
    },

    # TODO: consider adding more options
}
