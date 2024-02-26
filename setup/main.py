import sys
import os
import paramiko
from icecream import ic
from scp import SCPClient
import build_packages, networking, wg_keys

a_path = os.path.dirname(__file__)
sys.path.append("..")
from Thesis_scripts.vardata import ssh_conns, ptp_sec_cons


def main():
    for server in ssh_conns.values():

        ssh = createSSHClient(server[0], "root", "")
        scp = SCPClient(ssh.get_transport())

        # build_packages.do(ssh, scp)
        networking.do(ssh, scp, ptp_sec_cons)
        wg_keys.do(ssh, scp, ptp_sec_cons)


def createSSHClient(server, user, passw):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=passw)
    return client


if __name__ == "__main__":
    main()
