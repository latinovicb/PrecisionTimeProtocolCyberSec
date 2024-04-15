import paramiko
import argparse
import time
import os
from scp import SCPClient
import ptp_reader
import sec
import files_packages
import networking
import ptp_config_files
import stats_compare
from vardata import (
    ssh_conns,
    ptp_sec_cons,
    ptp_sec_cmds,
    ptp_log_config,
    ptp4l_log_match,
    netmask,
    PHY_INTERFACE,
    WG_INTERFACE,
    MACSEC_INTERFACE,
)

PHY_INTERFACE = PHY_INTERFACE.strip()
WG_INTERFACE = WG_INTERFACE.strip()
MACSEC_INTERFACE = MACSEC_INTERFACE.strip()


def measure(args):
    masters = ssh_conns["master"]
    slaves = ssh_conns["slave"]
    assert len(masters) == len(slaves)
    no_peers = len(masters)

    if not os.path.exists(ptp_log_config.location):
        os.makedirs(ptp_log_config.location)
        print("made ", ptp_log_config.location)
    else:
        print(ptp_log_config.location, " exists")

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
            remote_dir,
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
            remote_dir,
        )

        read_ptp = ptp_reader.PtpReader(
            ssh_master,
            scp_master,
            ssh_slave,
            scp_slave,
            ptp_sec_cmds,
            ptp_log_config,
            ptp4l_log_match,
        )

        setup(ssh_master, ssh_slave, scp_master, scp_slave, ptp_sec_cons, remote_dir)
        ###

        # each PTP mode must be defined in the vardata.py
        if args.nenc:
            if args.sw:
                read_ptp.do("no_enc_multicast_udp_sw")
                read_ptp.do("no_enc_multicast_l2_sw")
                read_ptp.do("no_enc_unicast_udp_sw")
                read_ptp.do("no_enc_unicast_l2_sw")

            if args.hw:
                read_ptp.do("no_enc_multicast_udp_hw")
                read_ptp.do("no_enc_multicast_l2_hw")
                read_ptp.do("no_enc_unicast_udp_hw")
                read_ptp.do("no_enc_unicast_l2_hw")

        if args.enc:
            wireguard.kill()
            wireguard.do()
            if args.sw:
                read_ptp.do("wg_enc_multicast_udp_sw")
                read_ptp.do("wg_enc_multicast_l2_sw")
            wireguard.kill()
            assert wireguard.status is False

            strongswan.kill()
            strongswan.do()
            if args.sw:
                read_ptp.do("ipsec_enc_unicast_udp_sw")
            if args.hw:
                read_ptp.do("ipsec_enc_unicast_udp_hw")
            strongswan.kill()
            assert strongswan.status is False

            macsec.kill()
            macsec.do()
            if args.sw:
                read_ptp.do("macsec_enc_multicast_udp_sw")
                read_ptp.do("macsec_enc_multicast_l2_sw")
            if args.hw:
                read_ptp.do("macsec_enc_unicast_udp_hw")
                read_ptp.do("macsec_enc_unicast_l2_hw")
            macsec.kill()
            assert macsec.status is False

        stats_compare.do(ptp_log_config.location, ptp_sec_cmds.keys(), ptp4l_log_match)

        if args.hw:
            stats_compare.do(ptp_log_config.location, ptp_sec_cmds.keys(), ptp4l_log_match, ts_type="hw")
        if args.sw:
            stats_compare.do(ptp_log_config.location, ptp_sec_cmds.keys(), ptp4l_log_match, ts_type="sw")

#
# def sec_set_mes(sec_obj, mes_obj):


def setup(ssh_master, ssh_slave, scp_master, scp_slave, interfaces, remote_dir):
    files_packages.do(ssh_master, scp_master)
    files_packages.do(ssh_slave, scp_master)
    networking.do(ssh_master,interfaces, PHY_INTERFACE, netmask)
    networking.do(ssh_slave,interfaces, PHY_INTERFACE, netmask)
    ptp_config_files.do(ssh_master,ssh_slave, interfaces,PHY_INTERFACE, remote_dir)


class CommandTimeout(Exception):
    pass


class MySSHClient(paramiko.SSHClient):
    def __init__(self, addr, user, passw):
        super().__init__()
        self.addr = addr
        self.stuck_cmd = 10  # timeout if there is not data comming from stdout -- keep it >10s just to be safe
        self.load_system_host_keys()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.connect(addr, username=user, password=passw)
        # try:
        # except paramiko.ssh_exception.BadHostKeyException as e:
        #     # assuming that .ssh is in ~
        #     os.system(f"ssh-keygen -f '/home/bl/.ssh/known_hosts' -R '{addr}'")

    def __stderr_check(self, stderr):
        errors = stderr.read().decode().strip()
        if errors:
            print(f"{self.addr} warning/err: {errors}")

    def run_command(self, command):
        """
        run single command with timeout handler
        """
        print(" : ", command)

        try:  # all single execution commands have specific timeout
            stdin, stdout, stderr = self.exec_command(command, timeout=self.stuck_cmd)
            self.__stderr_check(stderr)
            return stdout.read().decode().strip()
        except TimeoutError as e:
            print("timed out ", command)
            print(e)

    def run_continous(self, command, seconds):
        """
        to be used if long outputs are expected - generator with timer
        """
        start_time = time.time()
        stdin, stdout, stderr = self.exec_command(command, get_pty=True, timeout=self.stuck_cmd)
        try:
            for line in iter(stdout.readline, ""):
                if time.time() > start_time + seconds:
                    return
                yield line
        except TimeoutError:
            print(command, " done")


def main():
    parser = argparse.ArgumentParser(
        prog="analyzer_main",
        description='TODO',
    )
    parser.add_argument("-a", action="store_true", help="Enables everything")
    parser.add_argument("-sw", action="store_true", help="Enables measurement with software timestamping")
    parser.add_argument("-hw", action="store_true", help="Enables measurement with hardware timestamping")
    parser.add_argument("-nenc", action="store_true", help="Enables measurement with not encryption")
    parser.add_argument("-enc", action="store_true", help="Enables encryption tools where, each works with \
                        timestamping according to its capabilites \n \
                        must be also used with options above")

    args = parser.parse_args()

    if args.a:
        for arg in vars(args):
            print(arg, " set to true")
            setattr(args, arg, True)

    measure(args)


if __name__ == "__main__":
    main()
