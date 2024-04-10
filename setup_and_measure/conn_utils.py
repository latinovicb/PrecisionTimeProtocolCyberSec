import re

# Parent util class for security protocols -- private methods are accssed by children using name mangling


class SecUtils:
    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces, IFACE_PHY):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.interfaces = interfaces
        self.IFACE_PHY = IFACE_PHY
        self.status = "off"

    def get_status(self):
        return self.status

    def __change_status(self):
        self.status = "on" if self.status == "off" else "off"

    def __verify_connectivity(self, ssh, peer_addr):
        """
        Ping for 10 seconds
        """
        print("pinging ", peer_addr, " from ", ssh.addr)
        pattern = rf"(\d+) bytes from {re.escape(peer_addr)}: icmp_seq=(\d+) ttl=(\d+) time="
        matches = 0
        for reply in ssh.run_continous(f"ping {peer_addr}", 5):
            print(reply)
            if re.match(pattern, reply):
                matches += 1

        assert matches != 0

    def __generic_cmds(
        self, cmds, ssh, iface=None, do_format=False
    ):
        """
        Generic commands executed separately for each interface -- with additional parsing
        """

        for cmd in cmds:
            if do_format:
                addr_virt = self.interfaces[iface] + ssh.addr[-1]
                cmd = cmd.format(iface=iface, addr_virt=addr_virt, dst_dir=self.dst_dir)
            ssh.run_command(cmd)

    def __del_link(self, ssh, iface, dst_dir):
        print(f"Deleting link {iface} and {dst_dir}")
        ssh.run_command(f"rm -rf {dst_dir}")
        ssh.run_command(f"ip link del {iface}")

    def __gen_urandom_key(self):
        with open("/dev/urandom", "rb") as urandom:
            random_bytes = urandom.read(16)

        final = "".join([f"{byte:02x}" for byte in random_bytes])
        return final
