import re
import os
from logger import log
import pandas as pd
import pyshark
import matplotlib
import paramiko
import time
import numpy as np
import matplotlib.pyplot as plt

matplotlib.use("agg")
plt.yscale("symlog")  # symetric log


class MySSHClient(paramiko.SSHClient):
    def __init__(self, addr, user, passw):
        super().__init__()
        self.addr = addr
        # timeout if there is not data comming from stdout -- keep it >10s just to be safe
        self.stuck_cmd = 10
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.connect(addr, username=user, password=passw)
        self.run_command("mount -o remount,rw /")

    def __stderr_check(self, stderr):
        errors = stderr.read().decode().strip()
        if errors:
            log(f"{self.addr} warning/err: {errors}")

    def run_command(self, command, pty=True):
        """
        run single command with timeout handler
        """
        log(" : ", command)

        try:  # all single execution commands have specific timeout
            stdin, stdout, stderr = self.exec_command(
                command, get_pty=pty, timeout=self.stuck_cmd)
            self.__stderr_check(stderr)
            return stdout.read().decode().strip()
        except TimeoutError as e:
            log("Single exec. timed out ", command)
            log(e)
        except paramiko.SSHException as e:
            log("Single exec. channel timed out ", command)
            log(e)

    def run_continous(self, command, seconds):
        """
        to be used if long outputs are expected - generator with timer
        """
        start_time = time.time()
        try:
            stdin, stdout, stderr = self.exec_command(
                command, get_pty=True, timeout=self.stuck_cmd
            )
        except TimeoutError as e:
            log("Continous exec. timed out ", command)
            log(e)
        except paramiko.ssh_exception.SSHException as e:
            log("Continous exec. channel timed out", command)
            log(e)

        for line in iter(stdout.readline, ""):
            if time.time() > start_time + seconds:
                return
            yield line


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

        # doing average of averages -- THE LEN OF DATA MUST IS ALWAYS THE SAME
        self.means = {}
        plt.ion()
        # Increase pad to give more space, adjust w_pad and h_pad as needed
        plt.tight_layout(pad=5.0, w_pad=1.0, h_pad=2.0)
        plt.yscale("log")

    def __del__(self):
        plt.close(self.fig)

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


class PTPSinglePlotter(PlotUtils):
    def __init__(self, title, labels_units, location, plot_kwargs):
        super().__init__(title, labels_units, location, plot_kwargs)
        self.csv_first_write = True

    def update(self, data):
        self._PlotUtils__update(data)
        self.__save_csv(data)

    def __save_csv(self, data):
        name = f"{self.location.data}{self.title}.csv"
        if self.csv_first_write:
            log(f" ... rewriting/creating file {name}")
            data.to_csv(name, mode="w", header=True)
            self.csv_first_write = False
        else:
            log(f"Data_file UPDATED in {name}")
            data.to_csv(name, mode="a", header=False)


class PTPCombinedPlotter(PlotUtils):
    def __init__(self, title, labels_units, location, plot_kwargs):
        super().__init__(title, labels_units, location, plot_kwargs)
        # self.fig.suptitle(f"ptp4l data -- {title}")

    def update(self, data, line_name):
        self._PlotUtils__update(data, line_name, self.location.stats)

    def make_hist(self, data):
        for i in range(len(self.labels_units.keys()) - 1):
            self.__plot_hist(
                data,
                self.axs[i],
                list(self.labels_units.keys())[i + 1],
                list(self.labels_units.values())[i + 1],
            )
        self._PlotUtils__save_fig(self.location.hist)

    def make_box(self, data):
        for i in range(len(self.labels_units.keys()) - 1):
            self.__plot_box(
                data,
                self.axs[i],
                list(self.labels_units.keys())[i + 1],
                list(self.labels_units.values())[i + 1],
            )
        self._PlotUtils__save_fig(self.location.box)

    def __plot_box(self, data, ax, name, unit, line_name=None):
        ax.set_xlabel(f"{name} [{unit}]", fontsize=14)
        # ax.set_ylabel("count", labelpad=-5, fontsize=14)

        boxprops = dict(linestyle='-', linewidth=2, color='blue')
        whiskerprops = dict(linestyle='--', linewidth=2, color='orange')
        capprops = dict(linestyle='-', linewidth=2, color='green')
        flierprops = dict(marker='o', markerfacecolor='red',
                          markersize=12, linestyle='none', markeredgecolor='black')
        medianprops = dict(linestyle='-', linewidth=2, color='purple')

        ax.boxplot(data[name].dropna(), boxprops=boxprops, whiskerprops=whiskerprops,
                   capprops=capprops, flierprops=flierprops, medianprops=medianprops,
                   patch_artist=True, vert=False, whis=3.5)

    def __plot_hist(self, data, ax, name, unit):
        bin_size = int(2 * len(data) ** (1/3))  # rice method
        ax.set_xlabel(f"{name} [{unit}]", fontsize=14)
        # ax.set_ylabel("count", labelpad=-5, fontsize=14)
        ax.hist(data[name], bin_size)


def packets_time_delta(name, location, treshold, plot_kwargs):
    """
    Does not work for packets encrypted with ESP
    """
    pcap_file = location.caps + name + ".pcap"

    if os.path.exists(pcap_file):
        pass
    else:
        log("File does not exist ", pcap_file)
        return

    print(pcap_file)
    cap = pyshark.FileCapture(pcap_file)
    dst = location.p_delta + name
    ptp_timestamps = []
    for packet in cap:
        try:
            if 'PTP' in packet.highest_layer or 'ESP' in packet.highest_layer:
                ptp_timestamps.append(float(packet.sniff_timestamp))
        except AttributeError:
            continue

    ptp_timestamps = ptp_timestamps[treshold:]
    time_deltas = [ptp_timestamps[i] - ptp_timestamps[i-1]
                   for i in range(1, len(ptp_timestamps))]

    # Plotting the time deltas
    plt.figure(figsize=(1920 / 100, 1080 / 100), dpi=100)
    # plt.plot(time_deltas, marker='o', markersize=3, **plot_kwargs)
    ptp_timestamps.pop()
    plt.scatter(ptp_timestamps, time_deltas, s=1, alpha=0.5, color='blue')
    plt.xlabel('packet_index', fontsize=14)
    plt.ylabel('time_delta [s]', fontsize=14)
    plt.grid(True)
    plt.tight_layout(pad=5.0, w_pad=1.0, h_pad=1.0)
    log(f"Figure UPDATED in {dst}")
    plt.savefig(dst)
    plt.close()

    cap.close()
