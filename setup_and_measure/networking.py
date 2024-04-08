import subprocess
import re
import sys
from icecream import ic

IFACE_PHY = "eth1"
mask = "/24"

# needs to be redone
def do(ssh, scp, interfaces):
    ADDR = ssh.get_transport().getpeername()[0]
    ifaces = {
        IFACE_PHY: f"{interfaces[IFACE_PHY]}{ADDR[-1]}",
    }

    for iface, addr in ifaces.items():

        if check_iface(ssh, iface):
            ssh.exec_command(f"ip link set {iface}{mask} up")

        if check_addr(ssh, iface, addr, mask):
            ssh.exec_command(f"ip a a {addr}{mask} dev {iface}")


def check_iface(ssh, iface):
    output = ssh.run_command(f"ip a show {iface} up")

    # ssh.run_command(f"ip a flush {iface}")
    if output == "":
        return True


def check_addr(ssh, iface, addr, mask):
    output = ssh.run_command(
        "ip addr show %s | grep 'inet ' | awk '{print $2}'" % format(iface)
    )
    # output = str(stdout.read().decode())[:-1]  # last character is bogus

    if addr + mask != output:
        return True
