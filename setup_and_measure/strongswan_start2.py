import os
import re
from icecream import ic
import tempfile
from conn_utils import SecUtils


class StrongSwanSetup(SecUtils):

    def __init__(
        self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces, IFACE_PHY
    ):
        super().__init__(ssh_master, scp_master, ssh_slave, scp_slave, interfaces)
        self.IFACE_PHY = IFACE_PHY

    def do(self):
        self._SecUtils__change_status()
        try:
            ike_key = self._SecUtils__gen_urandom_key()
            self.__set_conf_file(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.interfaces,
                ike_key,
            )
            self.__set_conf_file(
                self.ssh_slave,
                self.ssh_master,
                self.IFACE_PHY,
                self.interfaces,
                ike_key,
            )
            self.__setup_peers(
                self.ssh_master, self.ssh_slave, self.IFACE_PHY, self.interfaces
            )

        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self._SecUtils__change_status()
        self.ssh_master.run_command("systemctl stop strongswan")
        self.ssh_slave.run_command("systemctl stop strongswan")

    def __set_conf_file(self, ssh_local, shh_remote, iface, interfaces, ike_key):
        local_addr = interfaces[iface] + ssh_local.get_transport().getpeername()[0][-1]
        remote_addr = (
            interfaces[iface] + shh_remote.get_transport().getpeername()[0][-1]
        )
        ### tmp variables
        enc_mode = "tunnel"
        local_ts = local_addr[:-1] + "0/24"
        remote_ts = local_ts
        protocol_type = "esp"
        enc_proposals = "aes256gcm128"
        ###

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

        self._SecUtils__generic_cmds(comms, ssh_local, do_format=False)

    def __setup_peers(self, ssh_master, ssh_slave, iface, interfaces):
        conn_status = ssh_master.run_command("swanctl -i --child ptp-conn")

        if "failed" in conn_status:
            print(conn_status)
            raise Exception

        addr_master = ssh_master.get_transport().getpeername()[0]
        addr_slave = ssh_slave.get_transport().getpeername()[0]

        self._SecUtils__verify_connectivity(
            ssh_master, f"{interfaces[iface]}{addr_slave[-1]}"
        )
        self._SecUtils__verify_connectivity(
            ssh_slave, f"{interfaces[iface]}{addr_master[-1]}"
        )
