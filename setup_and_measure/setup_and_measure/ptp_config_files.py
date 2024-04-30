def do_id_only(ssh_master, ssh_slave, dst_dir):
    __ptp_id_config(ssh_master, dst_dir)
    __ptp_id_config(ssh_slave, dst_dir)


def do_unicast(ssh_master, ssh_slave, interfaces, iface, dst_dir, mac):
    __ptp_unicast_slave(ssh_slave, ssh_master, interfaces, iface, dst_dir, mac)
    __ptp_unicast_master(ssh_master, dst_dir)


def do_ntp(ssh_master, dst_dir):
    # only master will need external time source
    __ntp_sync_server(ssh_master, dst_dir)


def __ptp_id_config(ssh, dst_dir):
    """
    needed just for wireguard - can be used anywhere
    """

    last_num = ssh.addr[-1]
    id_file = f"""\
[global]
clockIdentity           000000.0000.00000{last_num}
"""

    ssh.run_command("echo '" + id_file + f"' > /{dst_dir}/ptp_clock_id.cfg")


def __ptp_unicast_slave(ssh_slave, ssh_master, interfaces, iface, dst_dir, mac_addr):

    unicast_slave_file = f"""\
[unicast_master_table]
table_id                1
UDPv4                   {interfaces[iface] + ssh_master.addr[-1]}
L2                      {mac_addr}
[{iface}]
unicast_master_table    1
"""

    ssh_slave.run_command(
        "echo '" + unicast_slave_file +
        f"' > /{dst_dir}/unicast_slave_{iface}.cfg"
    )


def __ptp_unicast_master(ssh_master, dst_dir):
    """
    unicast master -- will always have custom id
    """

    unicast_master_file = """\
[global]
clockIdentity                   000000.0000.000001
hybrid_e2e                      1
inhibit_multicast_service       1
unicast_listen                  1
"""

    ssh_master.run_command(
        "echo '" + unicast_master_file + f"' > /{dst_dir}/unicast_master.cfg"
    )


def __ntp_sync_server(ssh_master, dst_dir):

    chrony_conf_file = """\
server ntp.nic.cz iburst minpoll 2 prefer
"""

    ssh_master.run_command(
        "echo '" + chrony_conf_file + f"' > /etc/chrony.conf")
    ssh_master.run_command("systemctl restart chronyd")
