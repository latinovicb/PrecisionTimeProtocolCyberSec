import os
import re
from icecream import ic
import tempfile
import conn_utils


class StrongSwanSetup:
    IFACE_PHY = "eth1"

    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.interfaces = interfaces
        self.status = "off"
        self.__change_status()

    def do(self):
        try:
            ike_key = conn_utils.gen_urandom_key()
            self._set_conf_file(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.interfaces,
                ike_key,
            )
            self._set_conf_file(
                self.ssh_slave,
                self.ssh_master,
                self.IFACE_PHY,
                self.interfaces,
                ike_key,
            )
            self._setup_peers(
                self.ssh_master, self.ssh_slave, self.IFACE_PHY, self.interfaces
            )

        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self.__change_status()
        self.ssh_master.run_command("systemctl stop strongswan")
        self.ssh_slave.run_command("systemctl stop strongswan")

    def get_status(self):
        return self.status

    def __change_status(self):
        self.status = "on" if self.status == "off" else "off"

    def _set_conf_file(self, ssh_local, shh_remote, iface, interfaces, ike_key):
        local_addr = interfaces[iface] + ssh_local.get_transport().getpeername()[0][-1]
        remote_addr = (
            interfaces[iface] + shh_remote.get_transport().getpeername()[0][-1]
        )
        enc_mode = "tunnel"
        local_ts = local_addr[:-1] + "0/24"
        remote_ts = local_ts
        protocol_type = "esp"
        enc_proposals = "aes256gcm128"

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

    def _setup_peers(self, ssh_master, ssh_slave, iface, interfaces):
        ssh_master.run_command("swanctl -i --child ptp-conn")

        addr_master = ssh_master.get_transport().getpeername()[0]
        addr_slave = ssh_slave.get_transport().getpeername()[0]

        conn_utils.verify_connectivity(
            ssh_master, f"{interfaces[iface]}{addr_slave[-1]}"
        )
        conn_utils.verify_connectivity(
            ssh_slave, f"{interfaces[iface]}{addr_master[-1]}"
        )
