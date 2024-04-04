import paramiko
import signal
import time
import sys
import os
from icecream import ic
from scp import SCPClient
import ptp_reader, wireguard_start2, macsec_start2, strongswan_start2

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
        ### objects
        ssh_master = MySSHClient(masters[i], ssh_user, ssh_pass)
        scp_master = SCPClient(ssh_master.get_transport())

        ssh_slave = MySSHClient(slaves[i], ssh_user, ssh_pass)
        scp_slave = SCPClient(ssh_slave.get_transport())

        wireguard = wireguard_start2.WireGuardSetup(
            ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons
        )
        strongswan = strongswan_start2.StrongSwanSetup(
            ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons
        )
        macsec = macsec_start2.MacsecSetup(
            ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons
        )
        ###

        # both sec and measuremnt will accpet args in the future

        wireguard.do()
        ptp_reader.do(ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons)
        wireguard.kill()
        assert wireguard.get_status() == "off"

        strongswan.do()
        ptp_reader.do(ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons)
        strongswan.kill()
        assert strongswan.get_status() == "off"

        macsec.do()
        ptp_reader.do(ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cons)
        macsec.kill()
        assert macsec.get_status() == "off"


#
# def sec_set_mes(sec_obj, mes_obj):


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

        timeout_t = str(10)  # all single execution commands have specific timeout
        try:
            stdin, stdout, stderr = self.exec_command(
                "timeout " + timeout_t + " " + command
            )
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
