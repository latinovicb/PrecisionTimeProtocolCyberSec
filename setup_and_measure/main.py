import paramiko
import time
from scp import SCPClient
import ptp_reader
import sec
import files_packages
import networking
import stats_compare
from vardata import (
    ssh_conns,
    ptp_sec_cons,
    ptp_sec_cmds,
    ptp_log_config,
    ptp4l_log_match,
    PHY_INTERFACE,
    WG_INTERFACE,
    MACSEC_INTERFACE,
)

PHY_INTERFACE = PHY_INTERFACE.strip()
WG_INTERFACE = WG_INTERFACE.strip()
MACSEC_INTERFACE = MACSEC_INTERFACE.strip()


def main():
    masters = ssh_conns["master"]
    slaves = ssh_conns["slave"]
    assert len(masters) == len(slaves)
    no_peers = len(masters)

    # extra logging info for master so that generators wouldn't bug -- maybe fix generators later
    for key, value in ptp_sec_cmds.items():
        ptp_sec_cmds[key]["master"] += " -l 7"

    for i in range(no_peers):
        # objects
        ssh_master = MySSHClient(masters[i].addr, masters[i].user, masters[i].passw)
        scp_master = SCPClient(ssh_master.get_transport())

        ssh_slave = MySSHClient(slaves[i].addr, slaves[i].user, slaves[i].passw)
        scp_slave = SCPClient(ssh_slave.get_transport())

        remote_dir = masters[i].dir  # assuming that master and slave will use same remote dir
        wireguard = sec.WireGuardSetup(
            ssh_master,
            scp_master,
            ssh_slave,
            scp_slave,
            ptp_sec_cons,
            PHY_INTERFACE,
            WG_INTERFACE,
            remote_dir
        )
        strongswan = sec.StrongSwanSetup(
            ssh_master,
            scp_master,
            ssh_slave,
            scp_slave,
            ptp_sec_cons,
            PHY_INTERFACE,
        )
        macsec = sec.MacsecSetup(
            ssh_master,
            scp_master,
            ssh_slave,
            scp_slave,
            ptp_sec_cons,
            PHY_INTERFACE,
            MACSEC_INTERFACE,
            remote_dir
        )

        read_ptp = ptp_reader.PtpReader(
            ssh_master, scp_master, ssh_slave, scp_slave, ptp_sec_cmds, ptp_log_config, ptp4l_log_match
        )

        ###

        # read_ptp.do("no_enc_multicast_udp_sw")
        # read_ptp.do("no_enc_multicast_l2_sw")
        read_ptp.do("no_enc_multicast_udp_hw")
        read_ptp.do("no_enc_multicast_l2_hw")
        # setup(ssh_master, ssh_slave, scp_master, scp_slave, ptp_sec_cons)

        # each mode must be defined in the vardata.py

        # wireguard.do()
        # wireguard.kill()
        # assert wireguard.get_status() == "off"

        # strongswan.do()
        # strongswan.kill()
        # assert strongswan.get_status() == "off"

        # macsec.do()
        # macsec.kill()
        # assert macsec.get_status() == "off"

        stats_compare.do(ptp_log_config.location, ptp4l_log_match)

#
# def sec_set_mes(sec_obj, mes_obj):


def setup(ssh_master, ssh_slave, scp_master, scp_slave, interfaces):
    files_packages.do(ssh_master, scp_master)
    files_packages.do(ssh_slave, scp_master)
    networking.do(ssh_master, scp_master, interfaces)
    networking.do(ssh_slave, scp_slave, interfaces)


class CommandTimeout(Exception):
    pass


class MySSHClient(paramiko.SSHClient):
    def __init__(self, server, user, passw):
        super().__init__()
        self.server = server
        self.load_system_host_keys()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.connect(server, username=user, password=passw)
        # try:
        # except paramiko.ssh_exception.BadHostKeyException as e:
        #     # assuming that .ssh is in ~
        #     os.system(f"ssh-keygen -f '/home/bl/.ssh/known_hosts' -R '{server}'")

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

        timeout_t = str(3)  # all single execution commands have specific timeout
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
