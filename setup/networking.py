import subprocess
import re
import sys
from icecream import ic


def do(ssh, scp, test_ifac):
    ADDR = ssh.get_transport().getpeername()[0]
    # ifac_phy = list(test_ifac)[0]
    # ifac_wg = list(test_ifac)[1]

    ifac_phy = "eth1"
    ifac_wg = "wg0"
    ifaces = {
        ifac_phy: f"{test_ifac[ifac_phy]}{ADDR[-1]}",
        ifac_wg: f"{test_ifac[ifac_wg]}{ADDR[-1]}",
    }
    mask = "/24"

    for iface, addr in ifaces.items():

        if check_iface(ssh, iface):
            ssh.exec_command(f"ip link set {iface}{mask} up")

        if check_addr(ssh, iface, addr, mask):
            ssh.exec_command(f"ip a a {addr}{mask} dev {iface}")


def check_iface(ssh, iface):
    # "doesn't work with wg"
    stdin, stdout, stderr = ssh.exec_command(f"ip a show {iface} up")
    output = stdout.read().decode()

    stdin, stdout, stderr = ssh.exec_command(f"ip a flush {iface}")
    output = stdout.read().decode()

    if output == "":
        return True


def check_addr(ssh, iface, addr, mask):
    stdin, stdout, stderr = ssh.exec_command(
        "ip addr show %s | grep 'inet ' | awk '{print $2}'" % format(iface)
    )
    output = str(stdout.read().decode())[:-1]  # last character is bogus

    if addr + mask != output:
        return True
