import os
import re
from icecream import ic
import tempfile
from conn_utils import SecUtils


class WireGuardSetup(SecUtils):
    IFACE_PHY = "eth1"
    IFACE_WG = "wg0"
    dst_dir = f"/tmp/{IFACE_WG}"  # just a tmp dir for purpose of creating keys

    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
        super().__init__(ssh_master, scp_master, ssh_slave, scp_slave, interfaces)

    def do(self):
        self._SecUtils__change_status()
        try:
            self.__setup_interfaces_keys(
                self.ssh_master, self.IFACE_WG, self.interfaces, self.dst_dir
            )
            self.__setup_interfaces_keys(
                self.ssh_slave, self.IFACE_WG, self.interfaces, self.dst_dir
            )
            self.__setup_peers(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.IFACE_WG,
                self.interfaces,
            )
            print("Okay")
        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self._SecUtils__change_status()
        self._SecUtils__del_link(self.ssh_master, self.IFACE_WG, self.dst_dir)
        self._SecUtils__del_link(self.ssh_slave, self.IFACE_WG, self.dst_dir)

    def __setup_interfaces_keys(self, ssh, iface, interfaces, dst_dir):
        wg_set_comms = (
            "mkdir {dst_dir}",
            "./wireguard-go {iface}",
            "wg genkey > {dst_dir}/private_key",
            "wg pubkey < {dst_dir}/private_key > {dst_dir}/public_key",
            "wg set {iface} private-key {dst_dir}/private_key",
            "ip link set {iface} up",
            "ip link set dev {iface} multicast on",
            "ip a a {addr_virt}/24 dev {iface}",
        )
        self._SecUtils__generic_cmds(wg_set_comms, ssh, iface, interfaces, dst_dir)
        # cmds, ssh, iface=None, interfaces=None, dst_dir=None, do_format=True

    def __setup_peers(self, ssh_master, ssh_slave, ifac_phy, ifac_wg, interfaces):
        pub_master, port_master = self.__get_wg_info(ssh_master, ifac_wg)
        pub_slave, port_slave = self.__get_wg_info(ssh_slave, ifac_wg)

        addr_slave = ssh_master.get_transport().getpeername()[0]
        addr_master = ssh_slave.get_transport().getpeername()[0]

        wg_addr_slave = self.__set_wg_peer(
            ssh_slave,
            addr_slave,
            pub_master,
            port_master,
            ifac_phy,
            ifac_wg,
            interfaces,
        )
        wg_addr_master = self.__set_wg_peer(
            ssh_master,
            addr_master,
            pub_slave,
            port_slave,
            ifac_phy,
            ifac_wg,
            interfaces,
        )

        self._SecUtils__verify_connectivity(ssh_master, wg_addr_master)
        self._SecUtils__verify_connectivity(ssh_slave, wg_addr_slave)

    def __get_wg_info(self, ssh, iface):
        public_key = ssh.run_command(f"wg show {iface} public-key")
        port_num = ssh.run_command(f"wg show {iface} listen-port")

        return public_key, port_num

    def __set_wg_peer(self, ssh, ADDR, pub, port, ifac_phy, ifac_wg, interfaces):
        ifaces = {
            ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
            ifac_wg: f"{interfaces[ifac_wg]}{ADDR[-1]}",
        }

        cmd = f"wg set {ifac_wg} peer {pub.strip()} allowed-ips {ifaces[ifac_wg]}/32,224.0.1.129/32,224.0.0.107/32 endpoint {ifaces[ifac_phy]}:{port}"
        ssh.run_command(cmd)

        return ifaces[ifac_wg]
