def do(ssh, interfaces, iface_phy,mask):
    addr = ssh.addr
    ifaces = {iface_phy: f"{interfaces[iface_phy]}{addr[-1]}",}

    for iface, addr in ifaces.items():
        ssh.run_command(f"ip link set {iface} up")
        if __check_addr(ssh, iface, addr, mask):
            ssh.exec_command(f"ip a a {addr}{mask} dev {iface}")
        print(addr + mask + " is set")


def __check_addr(ssh, iface, addr, mask):
    output = ssh.run_command("ip addr show %s | grep 'inet ' | awk '{print $2}'" % format(iface))
    if addr + mask != output:
        return True
