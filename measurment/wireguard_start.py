import os
import re
from icecream import ic
import tempfile
import conn_utils

IFACE_PHY = "eth1"
IFACE_WG = "wg0"


def do(ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
    dst_dir = f"/tmp/{IFACE_WG}"
    try:
        __seinterfacese_keys(ssh_master, IFACE_WG, interfaces, dst_dir)
        __seinterfacese_keys(ssh_slave, IFACE_WG, interfaces, dst_dir)
        __setup_peers(ssh_master, ssh_slave, IFACE_PHY, IFACE_WG, interfaces)
        print("Okay")
    except Exception as e:
        print(e)
        conn_utils.kill(ssh_master, IFACE_WG, dst_dir)
        conn_utils.kill(ssh_slave, IFACE_WG, dst_dir)
        return e


def __seinterfacese_keys(ssh, iface, interfaces, dst_dir):
    """
    Regualar commands for setting up tun interface and key
    """
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


def __setup_peers(ssh_master, ssh_slave, ifac_phy, ifac_wg, interfaces):

    pub_master, port_master = __get_wg_info(ssh_master, ifac_wg)
    pub_slave, port_slave = __get_wg_info(ssh_slave, ifac_wg)

    addr_slave = ssh_master.get_transport().getpeername()[0]
    addr_master = ssh_slave.get_transport().getpeername()[0]

    wg_addr_slave = __set_wg_peer(
        ssh_slave,
        addr_slave,
        pub_master,
        port_master,
        ifac_phy,
        ifac_wg,
        interfaces,
    )  # each peer for each other
    wg_addr_master = __set_wg_peer(
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


def __get_wg_info(ssh, iface):
    """
    Get public key and listen port for wireguard
    """

    public_key = ssh.run_command(f"wg show {iface} public-key")
    port_num = ssh.run_command(f"wg show {iface} listen-port")

    return public_key, port_num


def __set_wg_peer(ssh, ADDR, pub, port, ifac_phy, ifac_wg, interfaces):
    """
    Set peer device
    """

    ifaces = {
        ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
        ifac_wg: f"{interfaces[ifac_wg]}{ADDR[-1]}",
    }

    cmd = f"wg set {ifac_wg} peer {pub.strip()} allowed-ips {ifaces[ifac_wg]}/32,224.0.1.129/32,224.0.0.107/32 endpoint {ifaces[ifac_phy]}:{port}"
    ssh.run_command(cmd)

    return ifaces[ifac_wg]
