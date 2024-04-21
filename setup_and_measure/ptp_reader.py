import pandas as pd
import matplotlib.pyplot as plt
import re
from class_utils import PlotUtils
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)  # FIXME: df._append below


class PTPSinglePlotter(PlotUtils):
    def __init__(self, title, labels_units, location,plot_kwargs):
        super().__init__(title,labels_units,location,plot_kwargs)
        self.csv_first_write = True
        self.fig.suptitle(f"ptp4l parsed data -- {title}")

    def update(self, data):
        self._PlotUtils__update(data)
        self.__save_csv(data)

    def __save_csv(self, data):
        name = f"{self.location}/{self.title}.csv"
        if self.csv_first_write:
            print(f" ... rewriting/creating file {name}")
            data.to_csv(name, mode="w", header=True)
            self.csv_first_write = False
        else:
            print(f" appending to file {name}")
            data.to_csv(name, mode="a", header=False)


class PtpReader():
    def __init__(self, ssh_master, scp_master, ssh_slave, scp_slave, cmds, log_config, label_pattern):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.cmds = cmds

        self.labels_units = label_pattern.log_data
        self.pattern = label_pattern.re_pattern
        self.labels = list(self.labels_units.keys())

        self.timer = log_config.time
        self.buff_size = log_config.buff_size
        self.location = log_config.location

    def do(self, mode):
        """
        Read lines from ptp4l output
        """
        if mode not in self.cmds:
            print(f"'{mode}' mode is not defined!")

        ptp_cmd_master = self.cmds[mode]["master"]
        ptp_cmd_slave = self.cmds[mode]["slave"]

        print(
            "Running ptp reader with the following info: \n",
            "master: ",
            ptp_cmd_master,
            "\n",
            "slave: ",
            ptp_cmd_slave,
            "\n",
            "plot buff size: ",
            self.buff_size,
            "\n",
            "timer: ",
            self.timer,
            "\n",
            " ... initializing",
        )

        count = 0
        first_indx = 0
        plot_kwargs = {'linestyle':(0, (5, 10)), "color": "blue"}
        myPlt = PTPSinglePlotter(
            mode, self.labels_units, self.location, plot_kwargs
        )
        df = pd.DataFrame(
            columns=self.labels[1:],
        )

        for data in self.__run_sync(
            ptp_cmd_master,
            ptp_cmd_slave,
        ):
            # Fill by buff to ease the load
            if count == self.buff_size:
                # print("Passing data to plotter\n", df)
                myPlt.update(df)
                first_indx += count
                df = pd.DataFrame(
                    columns=self.labels[1:],
                )
                count = 0

            data = pd.Series(
                data, name=first_indx + count
            )  # NOTE: probably not very resource efficient
            df = df._append(data)  # FIXME: should be changed to concat
            count += 1
        myPlt.show_mean()

    def __run_sync(self, ptp_cmd_master, ptp_cmd_slave):
        """
        Run sync between server and master and return numbers which were parsed line by line
        """
        for line_m, line_s in zip(
            self.ssh_master.run_continous(ptp_cmd_master, self.timer),
            self.ssh_slave.run_continous(ptp_cmd_slave, self.timer),
        ):
            # print(line_m)
            # print(line_s)
            data = self.__parse_lines(line_s)
            log_time = 0

            if data:
                # log time is always bigger by one
                # TODO: maybe make dynamic
                if log_time != 0:
                    assert data["ptp4l_runtime"] == log_time + 1

                log_time = data.pop("ptp4l_runtime")

                yield data

    def __parse_lines(self, line):
        """
        Read floats from line and return parsed dict
        """

        tmp_dict = {}
        nums = []

        matches = re.findall(self.pattern, line)
        # Squash all signs TODO: error checking if maybe there are two errors next to each other
        for i in range(len(matches)):
            if matches[i] == "+" or matches[i] == "-":
                matches[i + 1] = matches[i] + matches[i + 1]
            else:
                nums.append(float(matches[i]))

        # Expected same number of values as existing labels
        if len(nums) == len(self.labels):
            for i in range(len(self.labels)):
                tmp_dict[self.labels[i]] = nums[i]

            return tmp_dict
