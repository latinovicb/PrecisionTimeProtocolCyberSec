# NOTE: moved to wireguard_start -- delete this file
def do(ssh, scp, test_ifac):
    # wg_iface = test_ifac.keys()[1]
    wg_iface = "wg0"
    stdin, stdout, stderr = ssh.exec_command(f"ip link show {wg_iface}")
    output = stdout.read().decode()

    if wg_iface in output:
        print(f"{wg_iface} exists; do nothing")
    else:
        # don't check interface check for configuraton
        print("no wireguard interface; generating keys")
        generate_keys_remote(ssh)
        set_keys(ssh, wg_iface)


def generate_keys_remote(ssh):
    ssh.exec_command("wg genkey > ~/private_key")
    ssh.exec_command("wg pubkey < ~/private_key > ~/public_key")


def set_keys(ssh, wg_iface):
    ssh.exec_command(f"./wireguard-go {wg_iface}")
    ssh.exec_command(f"wg set {wg_iface} private-key ~/private_key")
