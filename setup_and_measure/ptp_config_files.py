
def do(ssh_master, ssh_slave, interfaces, iface, dst_dir):

    __ptp_id_config(ssh_master,dst_dir)
    __ptp_id_config(ssh_slave,dst_dir)
    __ptp_unicast_slave(ssh_slave, ssh_master, interfaces, iface, dst_dir)
    __ptp_unicast_master(ssh_master, dst_dir)


def __ptp_id_config(ssh,dst_dir):
    """
    needed just for wireguard - can be used anywhere
    """

    last_num = ssh.addr[-1]
    id_file = f"""\
[global]
clockIdentity           000000.0000.00000{last_num}
"""

    ssh.run_command("echo '" + id_file + f"' > /{dst_dir}/ptp_clock_id.cfg")


def __ptp_unicast_slave(ssh_slave, ssh_master, interfaces, iface, dst_dir):

    unicast_slave_file = f"""\
[unicast_master_table]
table_id                1
UDPv4                   {interfaces[iface] + ssh_master.addr[-1]}
[eth1]
unicast_master_table    1
"""

    ssh_slave.run_command("echo '" + unicast_slave_file + f"' > /{dst_dir}/unicast_slave.cfg")


def __ptp_unicast_master(ssh_master, dst_dir):

    unicast_master_file = """\
[global]
hybrid_e2e                      1
inhibit_multicast_service       1
unicast_listen                  1
"""

    ssh_master.run_command("echo '" + unicast_master_file + f"' > /{dst_dir}/unicast_master.cfg")
