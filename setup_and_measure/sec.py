import re
from conn_utils import SecUtils


class WireGuardSetup(SecUtils):

    def __init__(
        self,
        ssh_master,
        scp_master,
        ssh_slave,
        scp_slave,
        interfaces,
        IFACE_PHY,
        IFACE_WG,
    ):
        super().__init__(ssh_master, scp_master, ssh_slave, scp_slave, interfaces)
        self.IFACE_PHY = IFACE_PHY
        self.IFACE_WG = IFACE_WG
        self.dst_dir = f"/tmp/{IFACE_WG}"  # just a tmp dir for purpose of creating keys

    def do(self):
        self._SecUtils__change_status()
        try:
            self.__setup_interfaces_keys(
                self.ssh_master, self.IFACE_WG, self.interfaces, self.dst_dir
            )
            self.__setup_interfaces_keys(
                self.ssh_slave, self.IFACE_WG, self.interfaces, self.dst_dir
            )
            self.__setup_peers(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.IFACE_WG,
                self.interfaces,
            )
            print("Okay")
        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self._SecUtils__change_status()
        self._SecUtils__del_link(self.ssh_master, self.IFACE_WG, self.dst_dir)
        self._SecUtils__del_link(self.ssh_slave, self.IFACE_WG, self.dst_dir)

    # def __set_ptp_config(self, sc):

    def __setup_interfaces_keys(self, ssh, iface, interfaces, dst_dir):
        wg_set_comms = (
            "mkdir {dst_dir}",
            "./wireguard-go {iface}",
            "wg genkey > {dst_dir}/private_key",
            "wg pubkey < {dst_dir}/private_key > {dst_dir}/public_key",
            "wg set {iface} private-key {dst_dir}/private_key",
            "ip link set {iface} up",
            "ip link set dev {iface} multicast on",
            "ip a a {addr_virt}/24 dev {iface}",
        )
        self._SecUtils__generic_cmds(wg_set_comms, ssh, iface, interfaces, dst_dir)
        # cmds, ssh, iface=None, interfaces=None, dst_dir=None, do_format=True

    def __setup_peers(self, ssh_master, ssh_slave, ifac_phy, ifac_wg, interfaces):
        pub_master, port_master = self.__get_wg_info(ssh_master, ifac_wg)
        pub_slave, port_slave = self.__get_wg_info(ssh_slave, ifac_wg)

        addr_slave = ssh_master.get_transport().getpeername()[0]
        addr_master = ssh_slave.get_transport().getpeername()[0]

        wg_addr_slave = self.__set_wg_peer(
            ssh_slave,
            addr_slave,
            pub_master,
            port_master,
            ifac_phy,
            ifac_wg,
            interfaces,
        )
        wg_addr_master = self.__set_wg_peer(
            ssh_master,
            addr_master,
            pub_slave,
            port_slave,
            ifac_phy,
            ifac_wg,
            interfaces,
        )

        self._SecUtils__verify_connectivity(ssh_master, wg_addr_master)
        self._SecUtils__verify_connectivity(ssh_slave, wg_addr_slave)

    def __get_wg_info(self, ssh, iface):
        public_key = ssh.run_command(f"wg show {iface} public-key")
        port_num = ssh.run_command(f"wg show {iface} listen-port")

        return public_key, port_num

    def __set_wg_peer(self, ssh, ADDR, pub, port, ifac_phy, ifac_wg, interfaces):
        ifaces = {
            ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
            ifac_wg: f"{interfaces[ifac_wg]}{ADDR[-1]}",
        }

        cmd = f"wg set {ifac_wg} peer {pub.strip()} allowed-ips {ifaces[ifac_wg]}/32,224.0.1.129/32,224.0.0.107/32 endpoint {ifaces[ifac_phy]}:{port}"
        ssh.run_command(cmd)

        return ifaces[ifac_wg]


class StrongSwanSetup(SecUtils):

    def __init__(
        self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces, IFACE_PHY
    ):
        super().__init__(ssh_master, scp_master, ssh_slave, scp_slave, interfaces)
        self.IFACE_PHY = IFACE_PHY

    def do(self):
        self._SecUtils__change_status()
        try:
            ike_key = self._SecUtils__gen_urandom_key()
            self.__set_conf_file(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.interfaces,
                ike_key,
            )
            self.__set_conf_file(
                self.ssh_slave,
                self.ssh_master,
                self.IFACE_PHY,
                self.interfaces,
                ike_key,
            )
            self.__setup_peers(
                self.ssh_master, self.ssh_slave, self.IFACE_PHY, self.interfaces
            )

        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self._SecUtils__change_status()
        self.ssh_master.run_command("systemctl stop strongswan")
        self.ssh_slave.run_command("systemctl stop strongswan")

    def __set_conf_file(self, ssh_local, shh_remote, iface, interfaces, ike_key):
        local_addr = interfaces[iface] + ssh_local.get_transport().getpeername()[0][-1]
        remote_addr = (
            interfaces[iface] + shh_remote.get_transport().getpeername()[0][-1]
        )
        # tmp variables
        enc_mode = "tunnel"
        local_ts = local_addr[:-1] + "0/24"
        remote_ts = local_ts
        protocol_type = "esp"
        enc_proposals = "aes256gcm128"
        ###

        file_content = f"""\
connections {{
    ptp-conn {{
        local_addrs = {local_addr}
        remote_addrs = {remote_addr}
        local {{
            auth = psk
        }}
        remote {{
            auth = psk
        }}

        children {{
            ptp-conn {{
                interface={iface}
                mode={enc_mode}
                local_ts={local_ts}
                remote_ts={remote_ts}
                {protocol_type}_proposals = {enc_proposals}
            }}
        }}
    }}
}}

secrets {{
   ike {{
      secret = {ike_key}
   }}
}}
"""

        comms = [
            "systemctl restart strongswan",
            "echo '" + file_content + "' > /etc/swanctl/conf.d/swanctl.conf",
        ]

        self._SecUtils__generic_cmds(comms, ssh_local, do_format=False)

    def __setup_peers(self, ssh_master, ssh_slave, iface, interfaces):
        conn_status = ssh_master.run_command("swanctl -i --child ptp-conn")

        if "failed" in conn_status:
            print(conn_status)
            raise Exception

        addr_master = ssh_master.get_transport().getpeername()[0]
        addr_slave = ssh_slave.get_transport().getpeername()[0]

        self._SecUtils__verify_connectivity(
            ssh_master, f"{interfaces[iface]}{addr_slave[-1]}"
        )
        self._SecUtils__verify_connectivity(
            ssh_slave, f"{interfaces[iface]}{addr_master[-1]}"
        )


class MacsecSetup(SecUtils):

    def __init__(
        self,
        ssh_master,
        scp_master,
        ssh_slave,
        scp_slave,
        interfaces,
        IFACE_PHY,
        IFACE_MACSEC,
    ):
        super().__init__(ssh_master, scp_master, ssh_slave, scp_slave, interfaces)
        self.IFACE_PHY = IFACE_PHY
        self.IFACE_MACSEC = IFACE_MACSEC
        self.dst_dir = f"/tmp/{IFACE_MACSEC}"

    def do(self):
        self._SecUtils__change_status()
        try:
            self.__setup_interfaces_keys(
                self.ssh_master,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            self.__setup_interfaces_keys(
                self.ssh_slave,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            self.__setup_peers(
                self.ssh_master,
                self.ssh_slave,
                self.IFACE_PHY,
                self.IFACE_MACSEC,
                self.interfaces,
                self.dst_dir,
            )
            print("Okay")
        except Exception as e:
            self.kill()
            raise e

    def kill(self):
        self._SecUtils__change_status()
        self._SecUtils__del_link(self.ssh_master, self.IFACE_MACSEC, self.dst_dir)
        self._SecUtils__del_link(self.ssh_slave, self.IFACE_MACSEC, self.dst_dir)

    def __setup_interfaces_keys(self, ssh, iface, interfaces, dst_dir):
        macsec_set_comms = (
            "mkdir {dst_dir}",
            "dd if=/dev/urandom count=16 bs=1 2> /dev/null | hexdump -e '1/2 \"%04x\"' > {dst_dir}/private_key",
            "ip link add link eth1 macsec0 type macsec encrypt on",
            "ip macsec add macsec0 tx sa 0 pn 100 on key 02 `cat {dst_dir}/private_key`",
            "ip a a {addr_virt}/24 dev {iface}",
        )
        self._SecUtils__generic_cmds(macsec_set_comms, ssh, iface, interfaces, dst_dir)

    def __setup_peers(
        self, ssh_master, ssh_slave, ifac_phy, ifac_macsec, interfaces, dst_dir
    ):
        mac_master, key_master = self.__get_mac_info(ssh_master, ifac_macsec, dst_dir)
        mac_slave, key_slave = self.__get_mac_info(ssh_slave, ifac_macsec, dst_dir)

        addr_slave = ssh_master.get_transport().getpeername()[0]
        addr_master = ssh_slave.get_transport().getpeername()[0]

        macsec_addr_slave = self.__set_mac_peer(
            ssh_slave,
            addr_slave,
            mac_master,
            ifac_phy,
            ifac_macsec,
            interfaces,
            key_master,
        )
        macsec_addr_master = self.__set_mac_peer(
            ssh_master,
            addr_master,
            mac_slave,
            ifac_phy,
            ifac_macsec,
            interfaces,
            key_slave,
        )

        self._SecUtils__verify_connectivity(ssh_master, macsec_addr_master)
        self._SecUtils__verify_connectivity(ssh_slave, macsec_addr_slave)

    def __get_mac_info(self, ssh, iface, dst_dir):
        iface_info = ssh.run_command(f"ip link show {iface}")
        mac_address = re.search(r"link/ether ([\w:]+)", iface_info).group(1)
        key = ssh.run_command(f"cat {dst_dir}/private_key")
        return mac_address, key

    def __set_mac_peer(self, ssh, ADDR, mac, ifac_phy, ifac_macsec, interfaces, key):
        ifaces = {
            ifac_phy: f"{interfaces[ifac_phy]}{ADDR[-1]}",
            ifac_macsec: f"{interfaces[ifac_macsec]}{ADDR[-1]}",
        }

        ssh.run_command(f"ip macsec add macsec0 rx address {mac} port 1")
        ssh.run_command(
            f"ip macsec add macsec0 rx address {mac} port 1 sa 0 pn 100 on key 02 {key}"
        )
        ssh.run_command(f"ip link set dev {ifac_macsec} up")

        return ifaces[ifac_macsec]
