import paramiko
import class_utils
import argparse
import time
from logger import log
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
        os.makedirs(ptp_log_config.location + "/data")
        os.makedirs(ptp_log_config.location + "/plots")
        os.makedirs(ptp_log_config.location + "/caps")
        log("made ", ptp_log_config.location)
    else:
        log(ptp_log_config.location, " exists")

    # extra log for master so that generators wouldn't bug -- maybe fix generators later
    for key, value in ptp_sec_cmds.items():
        ptp_sec_cmds[key]["master"] += " -l 7"

    for i in range(no_peers):
        # objects
        ssh_master = MySSHClient(
            masters[i].addr, masters[i].user, masters[i].passw)
        scp_master = SCPClient(ssh_master.get_transport())

        ssh_slave = MySSHClient(
            slaves[i].addr, slaves[i].user, slaves[i].passw)
        scp_slave = SCPClient(ssh_slave.get_transport())

        remote_dir = masters[
            i
        ].dir  # assuming that master and slave will use remote dir with the same name

        wireguard = sec.WireGuardSetup(
            ssh_master,
            ssh_slave,
            ptp_sec_cons,
            PHY_INTERFACE,
            WG_INTERFACE,
            remote_dir,
        )
        strongswan_tunl = sec.StrongSwanSetupTunnel(
            ssh_master,
            ssh_slave,
            ptp_sec_cons,
            PHY_INTERFACE,
            netmask,
        )
        strongswan_trans = sec.StrongSwanSetupTransport(
            ssh_master,
            ssh_slave,
            ptp_sec_cons,
            PHY_INTERFACE,
            netmask,
        )
        macsec = sec.MacsecSetup(
            ssh_master,
            ssh_slave,
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
            remote_dir,
        )
        args_status = any(value for value in vars(
            args).values() if value is True)  # do setup ops if atleast one arg is true
        if args_status:
            setup(ssh_master, ssh_slave, scp_master,
                  scp_slave, ptp_sec_cons, remote_dir)
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
                read_ptp.do("wg_enc_unicast_udp_sw")
            wireguard.kill()
            assert wireguard.status is False

            strongswan_tunl.kill()
            strongswan_tunl.do()
            if args.sw:
                read_ptp.do("ipsec_enc_unicast_udp_sw_tunnel")
            if args.hw:
                read_ptp.do("ipsec_enc_unicast_udp_hw_tunnel")
            strongswan_tunl.kill()
            assert strongswan_tunl.status is False

            strongswan_trans.kill()
            strongswan_trans.do()
            if args.sw:
                read_ptp.do("ipsec_enc_unicast_udp_sw_transport")
            if args.hw:
                read_ptp.do("ipsec_enc_unicast_udp_hw_transport")
            strongswan_trans.kill()
            assert strongswan_trans.status is False

            macsec.kill()
            macsec.do()
            if args.sw:
                read_ptp.do("macsec_enc_multicast_udp_sw")
                read_ptp.do("macsec_enc_multicast_l2_sw")

                read_ptp.do("macsec_enc_unicast_udp_sw")
                read_ptp.do("macsec_enc_unicast_l2_sw")
            if args.hw:
                read_ptp.do("macsec_enc_multicast_udp_hw")
                read_ptp.do("macsec_enc_multicast_l2_hw")

                read_ptp.do("macsec_enc_unicast_udp_hw")
                read_ptp.do("macsec_enc_unicast_l2_hw")
            macsec.kill()
            assert macsec.status is False

        stats_compare.do(ptp_log_config.location,
                         ptp_sec_cmds.keys(), ptp4l_log_match)

        if args.hw:
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="hw",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="hw",
                protocol="no_enc",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="hw",
                protocol="wg",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="hw",
                protocol="ipsec",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="hw",
                protocol="macsec",
            )
        if args.sw:
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="sw",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="sw",
                protocol="no_enc",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="sw",
                protocol="wg",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="sw",
                protocol="ipsec",
            )
            stats_compare.do(
                ptp_log_config.location,
                ptp_sec_cmds.keys(),
                ptp4l_log_match,
                ts_type="sw",
                protocol="macsec",
            )


# def sec_set_mes(sec_obj, mes_obj):


def setup(ssh_master, ssh_slave, scp_master, scp_slave, interfaces, remote_dir):
    files_packages.do(ssh_master, scp_master)
    files_packages.do(ssh_slave, scp_master)
    networking.do(ssh_master, interfaces, PHY_INTERFACE, netmask)
    networking.do(ssh_slave, interfaces, PHY_INTERFACE, netmask)

    ptp_config_files.do_id_only(ssh_master, ssh_slave, remote_dir)
    # ptp_config_files.do_ntp(ssh_master, remote_dir)

    mac_master = class_utils.SecUtils.get_mac_addr(ssh_master, PHY_INTERFACE)
    ptp_config_files.do_unicast(
        ssh_master, ssh_slave, interfaces, WG_INTERFACE, remote_dir, mac_master
    )  # wg
    ptp_config_files.do_unicast(
        ssh_master, ssh_slave, interfaces, PHY_INTERFACE, remote_dir, mac_master
    )  # strongswan
    ptp_config_files.do_unicast(
        ssh_master, ssh_slave, interfaces, MACSEC_INTERFACE, remote_dir, mac_master
    )  # macsec


class CommandTimeout(Exception):
    pass


class MySSHClient(paramiko.SSHClient):
    def __init__(self, addr, user, passw):
        super().__init__()
        self.addr = addr
        # timeout if there is not data comming from stdout -- keep it >10s just to be safe
        self.stuck_cmd = 10
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # current_user = os.getenv('USER')
        # command = f'ssh-keygen -f "/home/{current_user}/.ssh/known_hosts" -R "{addr}"'
        # os.system(command)

        self.connect(addr, username=user, password=passw)
        self.run_command("mount -o remount,rw /")

    def __stderr_check(self, stderr):
        errors = stderr.read().decode().strip()
        if errors:
            log(f"{self.addr} warning/err: {errors}")

    def run_command(self, command):
        """
        run single command with timeout handler
        """
        log(" : ", command)

        try:  # all single execution commands have specific timeout
            stdin, stdout, stderr = self.exec_command(
                command, timeout=self.stuck_cmd)
            self.__stderr_check(stderr)
            return stdout.read().decode().strip()
        except TimeoutError as e:
            log("timed out ", command)
            log(e)

    def run_continous(self, command, seconds):
        """
        to be used if long outputs are expected - generator with timer
        """
        start_time = time.time()
        stdin, stdout, stderr = self.exec_command(
            command, get_pty=True, timeout=self.stuck_cmd
        )
        try:
            for line in iter(stdout.readline, ""):
                if time.time() > start_time + seconds:
                    return
                yield line
        except TimeoutError as e:
            log(command, " -- command finished ", e)


def main():
    parser = argparse.ArgumentParser(
        prog="analyzer_main",
        description="TODO",
    )
    parser.add_argument("-a", action="store_true", help="Enable everything")
    parser.add_argument(
        "-sw",
        action="store_true",
        help="Enable measurement with software timestamping",
    )
    parser.add_argument(
        "-hw",
        action="store_true",
        help="Enable measurement with hardware timestamping",
    )
    parser.add_argument(
        "-nenc", action="store_true", help="Enable measurement with no encryption; \
                timestamping options must still be specified"
    )
    parser.add_argument(
        "-enc",
        action="store_true", help="Enable measurement with all encryption protocols; \
            timestamping options must still be specified"
    )

    args = parser.parse_args()

    if args.a:
        for arg in vars(args):
            log(arg, " set to true")
            setattr(args, arg, True)

    measure(args)


if __name__ == "__main__":
    main()
