import re
from logger import log
import pandas as pd
import pyshark
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("agg")
plt.yscale("symlog")  # symetric log


# Parent util class for security protocols -- private methods are accssed by children using name mangling
class SecUtils:
    def __init__(
        self, ssh_master, ssh_slave, interfaces, IFACE_PHY
    ):
        self.ssh_master = ssh_master
        self.ssh_slave = ssh_slave
        self.interfaces = interfaces
        self.IFACE_PHY = IFACE_PHY
        self.status = None

    def __verify_connectivity(self, ssh, peer_addr):
        """
        Ping for 10 seconds
        """
        log("pinging ", peer_addr, " from ", ssh.addr)
        pattern = (
            rf"(\d+) bytes from {re.escape(peer_addr)}: icmp_seq=(\d+) ttl=(\d+) time="
        )
        matches = 0
        for reply in ssh.run_continous(f"ping {peer_addr}", 5):
            log(reply)
            if re.match(pattern, reply):
                matches += 1

        assert matches != 0

    def __generic_cmds(self, cmds, ssh, iface=None, do_format=False):
        """
        Generic commands executed separately for each interface -- with additional parsing
        """

        for cmd in cmds:
            if do_format:
                addr_virt = self.interfaces[iface] + ssh.addr[-1]
                cmd = cmd.format(
                    iface=iface, addr_virt=addr_virt, dst_dir=self.dst_dir)
            ssh.run_command(cmd)

    def __del_link(self, ssh, iface, dst_dir):
        log(f"Deleting link {iface} and {dst_dir}")
        ssh.run_command(f"rm -rf {dst_dir}")
        ssh.run_command(f"ip link del {iface}")

    def __gen_urandom_key(self):
        with open("/dev/urandom", "rb") as urandom:
            random_bytes = urandom.read(16)

        final = "".join([f"{byte:02x}" for byte in random_bytes])
        return final

    @staticmethod
    def get_mac_addr(ssh, iface):
        iface_info = ssh.run_command(f"ip link show {iface}")
        mac_address = re.search(r"link/ether ([\w:]+)", iface_info).group(1)

        return mac_address


class PlotUtils:
    def __init__(self, title, labels_units, location, plot_kwargs):
        self.title = title
        self.location = location
        self.labels_units = labels_units
        self.plot_kwargs = plot_kwargs
        self.fig_type = ".png"
        self.fig, self.axs = plt.subplots(
            len(labels_units) - 1, figsize=(1920 / 100, 1080 / 100), dpi=100
        )
        for ax in self.axs:
            ax.grid()

        self.first_write = True
        # self.fig.suptitle(f"ptp4l parsed data -- {title}")
        # plt.rcParams["figure.figsize"] = [12.04, 7.68]

        # doing average of averages -- THE LEN OF DATA MUST IS ALWAYS THE SAME
        self.means = {}
        plt.ion()
        # Increase pad to give more space, adjust w_pad and h_pad as needed
        plt.tight_layout(pad=5.0, w_pad=1.0, h_pad=1.0)
        plt.yscale("log")

    def __update(self, data, line_name=None, location=None):
        if location is None:
            location = self.location.plots
        for i in range(len(self.labels_units.keys()) - 1):
            self.__plot_next(
                data,
                self.axs[i],
                list(self.labels_units.keys())[i + 1],
                list(self.labels_units.values())[i + 1],
                line_name,
            )

        self.__save_fig(location)

    # # to be called just with single row series -- ax position specified explicitely
    # def __simple_update(self, data, line_name, postiion):

    def __plot_next(self, data, ax, name, unit, line_name=None):
        # ax.title.set_text(name)
        ax.set_ylabel(f"{name} [{unit}]", fontsize=14)
        ax.set_xlabel("time [s]", labelpad=-5, fontsize=14)
        ax.scatter(data[name].index, data[name],
                   label=line_name, **self.plot_kwargs)
        ax.plot(data[name].index, data[name], alpha=0.7, **self.plot_kwargs)

        if name not in self.means:
            self.means[name] = (
                []
            )  # Create a new key with an empty list as its value if it doesn't exist
        self.means[name].append(data[name].mean())
        if line_name is not None:
            ax.legend(loc='upper right')

    def show_mean(self):
        for i in range(len(self.means.keys())):
            key = list(self.means.keys())[i]
            # rounded to 4 deciaml places
            total_mean = pd.Series(self.means[key]).mean()
            self.axs[i].axhline(
                y=total_mean,
                color="red",
                linestyle="--",
                label=f"{key}_mean",
            )
            self.axs[i].legend(loc='upper right', fontsize='large')
        self.__save_fig(self.location.plots)

    def __save_fig(self, location):
        name = f"{location}{self.title}"
        log(f"Figure UPDATED in {name}")
        plt.savefig(name + self.fig_type)


def packets_time_delta(name, location, treshold, plot_kwargs):
    """
    Does not work for packets encrypted with ESP
    """
    cap = pyshark.FileCapture(location.caps + name + ".pcap")
    dst = location.p_delta + name
    ptp_timestamps = []
    for packet in cap:
        try:
            if 'PTP' in packet.highest_layer:
                ptp_timestamps.append(float(packet.sniff_timestamp))
        except AttributeError:
            continue

    ptp_timestamps = ptp_timestamps[treshold:]
    time_deltas = [ptp_timestamps[i] - ptp_timestamps[i-1]
                   for i in range(1, len(ptp_timestamps))]

    # Plotting the time deltas
    plt.figure(figsize=(1920 / 100, 1080 / 100), dpi=100)
    plt.plot(time_deltas, marker='o', markersize=3, **plot_kwargs)
    plt.xlabel('packet_index', fontsize=14)
    plt.ylabel('time_delta [s]', fontsize=14)
    plt.grid(True)
    plt.tight_layout(pad=5.0, w_pad=1.0, h_pad=1.0)
    log(f"Figure UPDATED in {dst}")
    plt.savefig(dst)

    cap.close()
