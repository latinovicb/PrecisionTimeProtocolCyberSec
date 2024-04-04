import os
import re
from icecream import ic
import tempfile
import conn_utils


class MacsecSetup:
    IFACE_PHY = "eth1"
    IFACE_MACSEC = "macsec0"
    dst_dir = f"/tmp/{IFACE_MACSEC}"

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
            self._setup_interfaces_keys(
                self.ssh_master,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            self._setup_interfaces_keys(
                self.ssh_slave,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            self._setup_peers(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            print("Okay")
        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self.__change_status()
        conn_utils.kill(self.ssh_master, self.IFACE_MACSEC, self.dst_dir)
        conn_utils.kill(self.ssh_slave, self.IFACE_MACSEC, self.dst_dir)

    def get_status(self):
        return self.status

    def __change_status(self):
        self.status = "on" if self.status == "off" else "off"

    def _setup_interfaces_keys(self, ssh, iface, interfaces, dst_dir):
        macsec_set_comms = (
            "mkdir {dst_dir}",
            "dd if=/dev/urandom count=16 bs=1 2> /dev/null | hexdump -e '1/2 \"%04x\"' > {dst_dir}/private_key",
            "ip link add link eth1 macsec0 type macsec encrypt on",
            "ip macsec add macsec0 tx sa 0 pn 100 on key 02 `cat {dst_dir}/private_key`",
            "ip a a {addr_virt}/24 dev {iface}",
        )
        conn_utils.generic_cmds(macsec_set_comms, ssh, iface, interfaces, dst_dir)

    def _setup_peers(
        self, ssh_master, ssh_slave, ifac_phy, ifac_macsec, interfaces, dst_dir
    ):
        mac_master, key_master = self._get_mac_info(ssh_master, ifac_macsec, dst_dir)
        mac_slave, key_slave = self._get_mac_info(ssh_slave, ifac_macsec, dst_dir)

        addr_slave = ssh_master.get_transport().getpeername()[0]
        addr_master = ssh_slave.get_transport().getpeername()[0]

        macsec_addr_slave = self._set_mac_peer(
            ssh_slave,
            addr_slave,
            mac_master,
            ifac_phy,
            ifac_macsec,
            interfaces,
            key_master,
        )
        macsec_addr_master = self._set_mac_peer(
            ssh_master,
            addr_master,
            mac_slave,
            ifac_phy,
            ifac_macsec,
            interfaces,
            key_slave,
        )

        conn_utils.verify_connectivity(ssh_master, macsec_addr_master)
        conn_utils.verify_connectivity(ssh_slave, macsec_addr_slave)

    def _get_mac_info(self, ssh, iface, dst_dir):
        iface_info = ssh.run_command(f"ip link show {iface}")
        mac_address = re.search(r"link/ether ([\w:]+)", iface_info).group(1)
        key = ssh.run_command(f"cat {dst_dir}/private_key")
        return mac_address, key

    def _set_mac_peer(self, ssh, ADDR, mac, ifac_phy, ifac_macsec, interfaces, key):
        ifaces = {
            ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
            ifac_macsec: f"{interfaces[ifac_macsec]}{ADDR[-1]}",
        }

        ssh.run_command(f"ip macsec add macsec0 rx address {mac} port 1")
        ssh.run_command(
            f"ip macsec add macsec0 rx address {mac} port 1 sa 0 pn 100 on key 02 {key}"
        )
        ssh.run_command(f"ip link set dev {ifac_macsec} up")

        return ifaces[ifac_macsec]
