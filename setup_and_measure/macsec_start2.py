import os
import re
from icecream import ic
import tempfile
from conn_utils import SecUtils


class MacsecSetup(SecUtils):

    def __init__(
        self,
        ssh_master,
        scp_master,
        ssh_slave,
        scp_slave,
        interfaces,
        IFACE_PHY,
        IFACE_MACSEC,
    ):
        super().__init__(ssh_master, scp_master, ssh_slave, scp_slave, interfaces)
        self.IFACE_PHY = IFACE_PHY
        self.IFACE_MACSEC = IFACE_MACSEC
        self.dst_dir = f"/tmp/{IFACE_MACSEC}"

    def do(self):
        self._SecUtils__change_status()
        try:
            self.__setup_interfaces_keys(
                self.ssh_master,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            self.__setup_interfaces_keys(
                self.ssh_slave,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            self.__setup_peers(
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
        self._SecUtils__change_status()
        self._SecUtils__del_link(self.ssh_master, self.IFACE_MACSEC, self.dst_dir)
        self._SecUtils__del_link(self.ssh_slave, self.IFACE_MACSEC, self.dst_dir)

    def __setup_interfaces_keys(self, ssh, iface, interfaces, dst_dir):
        macsec_set_comms = (
            "mkdir {dst_dir}",
            "dd if=/dev/urandom count=16 bs=1 2> /dev/null | hexdump -e '1/2 \"%04x\"' > {dst_dir}/private_key",
            "ip link add link eth1 macsec0 type macsec encrypt on",
            "ip macsec add macsec0 tx sa 0 pn 100 on key 02 `cat {dst_dir}/private_key`",
            "ip a a {addr_virt}/24 dev {iface}",
        )
        self._SecUtils__generic_cmds(macsec_set_comms, ssh, iface, interfaces, dst_dir)

    def __setup_peers(
        self, ssh_master, ssh_slave, ifac_phy, ifac_macsec, interfaces, dst_dir
    ):
        mac_master, key_master = self.__get_mac_info(ssh_master, ifac_macsec, dst_dir)
        mac_slave, key_slave = self.__get_mac_info(ssh_slave, ifac_macsec, dst_dir)

        addr_slave = ssh_master.get_transport().getpeername()[0]
        addr_master = ssh_slave.get_transport().getpeername()[0]

        macsec_addr_slave = self.__set_mac_peer(
            ssh_slave,
            addr_slave,
            mac_master,
            ifac_phy,
            ifac_macsec,
            interfaces,
            key_master,
        )
        macsec_addr_master = self.__set_mac_peer(
            ssh_master,
            addr_master,
            mac_slave,
            ifac_phy,
            ifac_macsec,
            interfaces,
            key_slave,
        )

        self._SecUtils__verify_connectivity(ssh_master, macsec_addr_master)
        self._SecUtils__verify_connectivity(ssh_slave, macsec_addr_slave)

    def __get_mac_info(self, ssh, iface, dst_dir):
        iface_info = ssh.run_command(f"ip link show {iface}")
        mac_address = re.search(r"link/ether ([\w:]+)", iface_info).group(1)
        key = ssh.run_command(f"cat {dst_dir}/private_key")
        return mac_address, key

    def __set_mac_peer(self, ssh, ADDR, mac, ifac_phy, ifac_macsec, interfaces, key):
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
