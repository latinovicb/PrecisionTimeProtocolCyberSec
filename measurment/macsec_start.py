import os
import re
from icecream import ic
import tempfile
import conn_utils

IFACE_PHY = "eth1"
IFACE_MACSEC = "macsec0"


def do(ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
    dst_dir = f"/tmp/{IFACE_MACSEC}"
    try:
        __seinterfacese_keys(ssh_master, IFACE_MACSEC, interfaces, dst_dir)
        __seinterfacese_keys(ssh_slave, IFACE_MACSEC, interfaces, dst_dir)
        __setup_peers(
            ssh_master, ssh_slave, IFACE_PHY, IFACE_MACSEC, interfaces, dst_dir
        )
        print("Okay")
    except Exception as e:
        print(e)
        conn_utils.kill(ssh_master, IFACE_MACSEC, dst_dir)
        conn_utils.kill(ssh_slave, IFACE_MACSEC, dst_dir)
        return e


def __seinterfacese_keys(ssh, iface, interfaces, dst_dir):
    """
    Regualar commands for setting up tun interface and key
    """
    macsec_set_comms = (
        "mkdir {dst_dir}",
        "dd if=/dev/urandom count=16 bs=1 2> /dev/null | hexdump -e '1/2 \"%04x\"' > {dst_dir}/private_key",
        # "dd if=/dev/urandom count=16 bs=1 2> /dev/null | hexdump -e '1/2 \"%02x\"' > private_key",
        "ip link add link eth1 macsec0 type macsec encrypt on",
        "ip macsec add macsec0 tx sa 0 pn 100 on key 02 `cat {dst_dir}/private_key`",
        "ip a a {addr_virt}/24 dev {iface}",
    )
    conn_utils.generic_cmds(macsec_set_comms, ssh, iface, interfaces, dst_dir)


def __setup_peers(ssh_master, ssh_slave, ifac_phy, ifac_wg, interfaces, dst_dir):

    mac_master, key_master = __get_mac_info(ssh_master, ifac_wg, dst_dir)
    mac_slave, key_slave = __get_mac_info(ssh_slave, ifac_wg, dst_dir)

    addr_slave = ssh_master.get_transport().getpeername()[0]
    addr_master = ssh_slave.get_transport().getpeername()[0]

    macsec_addr_slave = __set_mac_peer(
        ssh_slave, addr_slave, mac_master, ifac_phy, ifac_wg, interfaces, key_master
    )
    macsec_addr_master = __set_mac_peer(
        ssh_master, addr_master, mac_slave, ifac_phy, ifac_wg, interfaces, key_slave
    )

    # Connectivity works -- fix the issue with the method and signal.signal

    # conn_utils.verify_connectivity(ssh_master, macsec_addr_master)
    # conn_utils.verify_connectivity(ssh_slave, macsec_addr_slave)


def __get_mac_info(ssh, iface, dst_dir):
    """
    Get mac address
    """

    iface_info = ssh.run_command(f"ip link show {iface}")
    mac_address = re.search(r"link/ether ([\w:]+)", iface_info).group(1)

    # TODO: exchange keys directly between devies, don't copy it here
    key = ssh.run_command(f"cat {dst_dir}/private_key")

    return mac_address, key


def __set_mac_peer(ssh, ADDR, mac, ifac_phy, ifac_wg, interfaces, key):
    """
    Set peer device
    """

    ifaces = {
        ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
        ifac_wg: f"{interfaces[ifac_wg]}{ADDR[-1]}",
    }

    # cmd = f"wg set {ifac_wg} peer {pub.strip()} allowed-ips {ifaces[ifac_wg]}/32,224.0.1.129/32,224.0.0.107/32 endpoint {ifaces[ifac_phy]}:{port}"
    ssh.run_command(f"ip macsec add macsec0 rx address {mac} port 1")
    ssh.run_command(
        f"ip macsec add macsec0 rx address {mac} port 1 sa 0 pn 100 on key 02 {key}"
    )

    # can be set to up only after peers are configured
    ssh.run_command(f"ip link set dev {ifac_wg} up")

    return ifaces[ifac_wg]
