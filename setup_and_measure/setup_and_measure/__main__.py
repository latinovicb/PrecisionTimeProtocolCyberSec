import argparse
from logger import log
import os
from scp import SCPClient
import ptp_reader
import sec
import files_packages
import networking
import ptp_config_files
import stats_compare
from class_utils import SecUtils, MySSHClient
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

    for field in ptp_log_config.location.__dataclass_fields__:
        dir = getattr(ptp_log_config.location, field)
        make_dir(dir)

    # extra log for master so that generators wouldn't bug
    for key, value in ptp_sec_cmds.items():
        ptp_sec_cmds[key]["master"] += " -l 7"

    for i in range(no_peers):
        # objects
        if args.mes:
            log("DO MES")
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

            if args.ntp:
                ptp_config_files.do_ntp(ssh_master, remote_dir)

            if args.pull:
                files_packages.do(ssh_master, scp_master)
                files_packages.do(ssh_slave, scp_master)

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

        if args.stat:
            log("DO STAT")
            stat_comp = stats_compare.StatMakerComparator(
                ptp_log_config.location, ptp_sec_cmds.keys(), ptp4l_log_match)

            if args.hw:
                stat_comp.do(ts_type="hw", do_stats=True)
                stat_comp.do(ts_type="hw")
                stat_comp.do(ts_type="hw", protocol="no_enc")
                stat_comp.do(ts_type="hw", protocol="wg")
                stat_comp.do(ts_type="hw", protocol="ipsec")
                stat_comp.do(ts_type="hw", protocol="macsec")
            if args.sw:
                stat_comp.do(ts_type="sw", do_stats=True)
                stat_comp.do(ts_type="sw")
                stat_comp.do(ts_type="sw", protocol="no_enc")
                stat_comp.do(ts_type="sw", protocol="wg",)
                stat_comp.do(ts_type="sw", protocol="ipsec")
                stat_comp.do(ts_type="sw", protocol="macsec")

            # stat_comp.do()
            if args.packets:
                stat_comp.do(do_packets=True)


def setup(ssh_master, ssh_slave, scp_master, scp_slave, interfaces, remote_dir):
    networking.do(ssh_master, interfaces, PHY_INTERFACE, netmask)
    networking.do(ssh_slave, interfaces, PHY_INTERFACE, netmask)

    ptp_config_files.do_id_only(ssh_master, ssh_slave, remote_dir)

    mac_master = SecUtils.get_mac_addr(ssh_master, PHY_INTERFACE)
    ptp_config_files.do_unicast(
        ssh_master, ssh_slave, interfaces, WG_INTERFACE, remote_dir, mac_master
    )  # wg
    ptp_config_files.do_unicast(
        ssh_master, ssh_slave, interfaces, PHY_INTERFACE, remote_dir, mac_master
    )  # strongswan
    ptp_config_files.do_unicast(
        ssh_master, ssh_slave, interfaces, MACSEC_INTERFACE, remote_dir, mac_master
    )  # macsec


def make_dir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        log("made ", dir_name)
    else:
        log(dir_name, " exists")


def main():
    parser = argparse.ArgumentParser(
        prog="analyzer_main",
        description="Configuration, Measurement and Analysis tool; Specify additional options in confdata.yml",
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
                Timestamping options must still be specified"
    )
    parser.add_argument(
        "-enc",
        action="store_true", help="Enable measurement with all encryption protocols; \
            Timestamping options must still be specified"
    )
    parser.add_argument("-stat", action="store_true",
                        help="Do statistics and plot comparisons \
                        (There must be existing data in dir)")
    parser.add_argument("-mes", action="store_true",
                        help="Do measurment on provided Master & Slave devices")
    parser.add_argument("-packets", action="store_true",
                        help="Run packet analysis & plotting")
    parser.add_argument("-ntp", action="store_true",
                        help="Enable NTP synchronization on Master")
    parser.add_argument("-pull", action="store_true",
                        help="Pull and cross-compile nessacary packages")
    args = parser.parse_args()

    if args.a:
        for arg in vars(args):
            log(arg, " set to true")
            setattr(args, arg, True)

    measure(args)


if __name__ == "__main__":
    main()
