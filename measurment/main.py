import paramiko
import signal
import time
import sys
import os
from icecream import ic
from scp import SCPClient
import ptp_reader, wireguard_start, macsec_start

a_path = os.path.dirname(__file__)
sys.path.append("..")
from Thesis_scripts.vardata import ssh_conns, ptp_sec_cons

ssh_user = "root"
ssh_pass = ""


def main():
    masters = ssh_conns["master"]
    slaves = ssh_conns["slave"]
    assert len(masters) == len(slaves)
    no_peers = len(masters)

    for i in range(no_peers):
        ssh_master = MySSHClient(masters[i], ssh_user, ssh_pass)
        scp_master = SCPClient(ssh_master.get_transport())

        ssh_slave = MySSHClient(slaves[i], ssh_user, ssh_pass)
        scp_slave = SCPClient(ssh_slave.get_transport())

        # wireguard_start.do(ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons)

        macsec_start.do(ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons)

        # ptp_reader.do(ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons)


class CommandTimeout(Exception):
    pass


class MySSHClient(paramiko.SSHClient):
    def __init__(self, server, user, passw):
        super().__init__()
        self.server = server
        self.load_system_host_keys()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect(server, username=user, password=passw)

    def __error_check(self, stderr):
        errors = stderr.read().decode().strip()
        if errors:
            # raise Exception(f"{self.server}: {errors}")
            print(f"{self.server}: {errors}")

    def __handler(self, signum, frame):
        raise CommandTimeout(f"Timed out {signum}, {frame}")

    def run_command(self, command):
        """
        run single command with timeout handler
        """
        print(" : ", command)

        signal.signal(signal.SIGALRM, self.__handler)
        signal.alarm(5)
        try:
            stdin, stdout, stderr = self.exec_command(command)
            self.__error_check(stderr)
            return stdout.read().decode().strip()
        except CommandTimeout:
            print("Command timeout: ", command)
            return

    def run_continous(self, command, seconds):
        """
        to be used if long outputs are expected - generator with timer
        """
        start_time = time.time()
        stdin, stdout, stderr = self.exec_command(command, get_pty=True)

        for line in iter(stdout.readline, ""):
            if time.time() > start_time + seconds:
                return
            yield line


if __name__ == "__main__":
    main()
