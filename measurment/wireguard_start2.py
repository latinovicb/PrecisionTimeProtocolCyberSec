import os
import re
from icecream import ic
import tempfile
import conn_utils


class WireGuardSetup:
    IFACE_PHY = "eth1"
    IFACE_WG = "wg0"

    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.interfaces = interfaces

    def do(self):
        dst_dir = f"/tmp/{self.IFACE_WG}"
        try:
            self._setup_interfaces_keys(
                self.ssh_master, self.IFACE_WG, self.interfaces, dst_dir
            )
            self._setup_interfaces_keys(
                self.ssh_slave, self.IFACE_WG, self.interfaces, dst_dir
            )
            self._setup_peers(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.IFACE_WG,
                self.interfaces,
            )
            print("Okay")
        except Exception as e:
            conn_utils.kill(self.ssh_master, self.IFACE_WG, dst_dir)
            conn_utils.kill(self.ssh_slave, self.IFACE_WG, dst_dir)
            raise e

    def _setup_interfaces_keys(self, ssh, iface, interfaces, dst_dir):
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
        conn_utils.generic_cmds(wg_set_comms, ssh, iface, interfaces, dst_dir)

    def _setup_peers(self, ssh_master, ssh_slave, ifac_phy, ifac_wg, interfaces):
        pub_master, port_master = self._get_wg_info(ssh_master, ifac_wg)
        pub_slave, port_slave = self._get_wg_info(ssh_slave, ifac_wg)

        addr_slave = ssh_master.get_transport().getpeername()[0]
        addr_master = ssh_slave.get_transport().getpeername()[0]

        wg_addr_slave = self._set_wg_peer(
            ssh_slave,
            addr_slave,
            pub_master,
            port_master,
            ifac_phy,
            ifac_wg,
            interfaces,
        )
        wg_addr_master = self._set_wg_peer(
            ssh_master,
            addr_master,
            pub_slave,
            port_slave,
            ifac_phy,
            ifac_wg,
            interfaces,
        )

        conn_utils.verify_connectivity(ssh_master, wg_addr_master)
        conn_utils.verify_connectivity(ssh_slave, wg_addr_slave)

    def _get_wg_info(self, ssh, iface):
        public_key = ssh.run_command(f"wg show {iface} public-key")
        port_num = ssh.run_command(f"wg show {iface} listen-port")

        return public_key, port_num

    def _set_wg_peer(self, ssh, ADDR, pub, port, ifac_phy, ifac_wg, interfaces):
        ifaces = {
            ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
            ifac_wg: f"{interfaces[ifac_wg]}{ADDR[-1]}",
        }

        cmd = f"wg set {ifac_wg} peer {pub.strip()} allowed-ips {ifaces[ifac_wg]}/32,224.0.1.129/32,224.0.0.107/32 endpoint {ifaces[ifac_phy]}:{port}"
        ssh.run_command(cmd)

        return ifaces[ifac_wg]
