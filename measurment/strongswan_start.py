import os
import re
from icecream import ic
import tempfile
import conn_utils

IFACE_PHY = "eth1"


### this will have to be significantly different than previous two setups


def do(ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
    try:
        ike_key = conn_utils.gen_urandom_key()
        __set_conf_file(ssh_master, ssh_slave, IFACE_PHY, interfaces, ike_key)
        __set_conf_file(ssh_slave, ssh_master, IFACE_PHY, interfaces, ike_key)
        __setup_peers(ssh_master, ssh_slave)

    except Exception as e:
        raise e


def __set_conf_file(ssh_local, shh_remote, iface, interfaces, ike_key):
    """
    Creation of file used as a configuration for swanctl
    """

    ### tmp vars -- move outside
    local_addr = interfaces[iface] + ssh_local.get_transport().getpeername()[0][-1]
    remote_addr = interfaces[iface] + shh_remote.get_transport().getpeername()[0][-1]
    enc_mode = "tunnel"  # ~
    local_ts = local_addr[:-1] + "0/24"
    remote_ts = local_ts
    protocol_type = "esp"  # either esp or ah #~
    enc_proposals = (
        "aes256gcm128"  # THIS MUST BE COMPATIBLE WITH ABOVE SPECIFIED PROTOCOL #~
    )
    ###

    # formatting done here
    file_content = f"""\
connections {{
    ptp-conn {{
        local_addrs = {local_addr}
        remote_addrs = {remote_addr}
        local {{
            auth = psk
        }}
        remote {{
            auth = psk
        }}

        children {{
            ptp-conn {{
                interface={iface}
                mode={enc_mode}
                local_ts={local_ts}
                remote_ts={remote_ts}
                {protocol_type}_proposals = {enc_proposals}
            }}
        }}
    }}
}}

secrets {{
   ike {{
      secret = {ike_key}
   }}
}}
"""

    comms = [
        "systemctl restart strongswan",
        "echo '" + file_content + "' > /etc/swanctl/conf.d/swanctl.conf",
    ]

    conn_utils.generic_cmds(comms, ssh_local, do_format=False)


def __setup_peers(ssh_master, ssh_slave):

    ssh_master.run_command("swanctl -i --child ptp-conn")
    conn_utils.verify_connectivity(
        ssh_master, ssh_slave.get_transport().getpeername()[0]
    )
    conn_utils.verify_connectivity(
        ssh_slave, ssh_master.get_transport().getpeername()[0]
    )
