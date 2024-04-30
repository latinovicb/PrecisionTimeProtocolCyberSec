import re
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("agg")
plt.yscale('symlog')  # symetric log

# Parent util class for security protocols -- private methods are accssed by children using name mangling
class SecUtils:
    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, interfaces, IFACE_PHY):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.interfaces = interfaces
        self.IFACE_PHY = IFACE_PHY
        self.status = None

    def __verify_connectivity(self, ssh, peer_addr):
        """
        Ping for 10 seconds
        """
        print("pinging ", peer_addr, " from ", ssh.addr)
        pattern = rf"(\d+) bytes from {re.escape(peer_addr)}: icmp_seq=(\d+) ttl=(\d+) time="
        matches = 0
        for reply in ssh.run_continous(f"ping {peer_addr}", 5):
            print(reply)
            if re.match(pattern, reply):
                matches += 1

        assert matches != 0

    def __generic_cmds(
        self, cmds, ssh, iface=None, do_format=False
    ):
        """
        Generic commands executed separately for each interface -- with additional parsing
        """

        for cmd in cmds:
            if do_format:
                addr_virt = self.interfaces[iface] + ssh.addr[-1]
                cmd = cmd.format(iface=iface, addr_virt=addr_virt, dst_dir=self.dst_dir)
            ssh.run_command(cmd)

    def __del_link(self, ssh, iface, dst_dir):
        print(f"Deleting link {iface} and {dst_dir}")
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
        self.fig_type = ".svg"
        self.fig, self.axs = plt.subplots(len(labels_units) - 1, figsize=(1920/100, 1080/100), dpi=300)

        self.first_write = True
        self.fig.suptitle(f"ptp4l parsed data -- {title}")
        # plt.rcParams["figure.figsize"] = [12.04, 7.68]

        # doing average of averages -- THE LEN OF DATA MUST IS ALWAYS THE SAME
        self.means = {}
        plt.ion()
        plt.yscale('log')

    def __update(self, data, line_name=None):
        for i in range(len(self.labels_units.keys()) - 1):
            self.__plot_next(
                data,
                self.axs[i],
                list(self.labels_units.keys())[i + 1],
                list(self.labels_units.values())[i + 1],
                line_name,
            )

        self.__save_fig()

    # # to be called just with single row series -- ax position specified explicitely
    # def __simple_update(self, data, line_name, postiion):

    def __plot_next(self, data, ax, name, unit, line_name=None):
        ax.title.set_text(name)
        ax.set(ylabel=unit)
        ax.scatter(data[name].index, data[name], label=line_name, **self.plot_kwargs)
        ax.plot(data[name].index, data[name], alpha=0.7, **self.plot_kwargs)


        if name not in self.means:
            self.means[name] = []  # Create a new key with an empty list as its value if it doesn't exist
        self.means[name].append(data[name].mean())
        if line_name is not None:
            ax.legend()

    def show_mean(self):
        for i in range(len(self.means.keys())):
            key = list(self.means.keys())[i]
            total_mean = round(pd.Series(self.means[key]).mean(), 4)  # rounded to 4 deciaml places
            self.axs[i].axhline(y=total_mean,color='red',linestyle='--',label=f"{key}_mean: {total_mean}")
            self.axs[i].legend()
        self.__save_fig()

    def __save_fig(self):
        name = f"{self.location}/plots/{self.title}"
        print(f"Figure updated/saved to {name}")
        plt.savefig(name + self.fig_type)
