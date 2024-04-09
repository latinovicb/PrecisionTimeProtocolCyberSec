import re

# Parent util class for security protocols -- private methods are accssed by children using name mangling


class SecUtils:
    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.interfaces = interfaces
        self.status = "off"

    def get_status(self):
        return self.status

    def __change_status(self):
        self.status = "on" if self.status == "off" else "off"

    def __verify_connectivity(self, ssh, addr):
        """
        Ping for 10 seconds
        """
        pattern = rf"(\d+) bytes from {re.escape(addr)}: icmp_seq=(\d+) ttl=(\d+) time="
        matches = 0
        for reply in ssh.run_continous(f"ping {addr}", 5):
            print(reply)
            if re.match(pattern, reply):
                matches += 1

        assert matches != 0

    def __generic_cmds(
        self, cmds, ssh, iface=None, interfaces=None, dst_dir=None, do_format=True
    ):
        """
        Generic commands executed separately for each interface -- with additional parsing
        """
        if do_format:
            addr = ssh.get_transport().getpeername()[0]
            addr_virt = interfaces[iface] + addr[-1]

        for cmd in cmds:
            if do_format:
                cmd = cmd.format(iface=iface, addr_virt=addr_virt, dst_dir=dst_dir)
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
