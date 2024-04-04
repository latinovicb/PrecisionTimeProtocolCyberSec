import pandas as pd
import re
import matplotlib
import matplotlib.pyplot as plt

# Find all matches in the line
pattern = r"(?:\b[+\-]?\d+(?:\.\d+)?\b\s*(?![-+])|[+\-])"
labels = ["ptp4l_runtime", "master_offset", "s2_freq", "path_delay"]


def do(ssh_master, scp_master, ssh_slave, scp_slave, test_ifac):
    """
    Read lines from ptp4l output
    """

    ### Tmp vars -- should be taken as an arguments from main
    timer = 60
    ptp_cmd_master = "ptp4l -m -i eth1 -l 7 -f settings.cfg"  # extra logging info for master so that generators wouldn't bug -- maybe fix generators later
    ptp_cmd_slave = "ptp4l -m -s -i eth1 -f settings.cfg"
    buff_size = 10
    title = "no enc."
    location = "/tmp"
    save_period = 1
    ###
    print(
        "Runninge ptp reader with following info: ",
        timer,
        ptp_cmd_master,
        ptp_cmd_slave,
        buff_size,
    )

    count = 0
    first_indx = 0
    myPlt = PlotSaver(title, location, save_period)
    df = pd.DataFrame(
        columns=labels[1:],
    )

    for data in __run_sync(ssh_master, ssh_slave, ptp_cmd_master, ptp_cmd_slave, timer):
        # Fill by buff to ease the load
        if count == buff_size:
            myPlt.update(df)
            first_indx += count
            df = pd.DataFrame(
                columns=labels[1:],
            )
            count = 0

        # This is probably not very resource efficient
        data = pd.Series(data, name=first_indx + count)
        print(data)
        df = df._append(data)
        # df = pd.concat([df, data], axis=0)
        count += 1
        print(df)


class PlotSaver:
    def __init__(self, title, location, save_period):
        self.location = location
        self.save_period = save_period
        self.fig, self.axs = plt.subplots(2, 2, figsize=(16, 9), dpi=200)
        self.fig.suptitle(f"ptp4l parsed data -- {title}")
        # plt.rcParams["figure.figsize"] = [12.04, 7.68]
        plt.ion()

    def update(self, data):
        print(data)
        self.axs[0, 0].plot(data["master_offset"], label="master_offset")
        self.axs[0, 1].plot(data["s2_freq"], label="s2_freq")
        self.axs[1, 0].plot(data["path_delay"], label="path_delay")

        # for ax in self.axs.flatten():
        #     ax.legend()

        # self.fig.canvas.draw()
        self.__save_fig()

    def __save_fig(self):
        plt.savefig(f"{self.location}/ptp_data")


def __run_sync(ssh_master, ssh_slave, ptp_cmd_master, ptp_cmd_slave, timer):
    """
    Run sync between server and master and return numbers which were parsed line by line
    """
    for line_m, line_s in zip(
        ssh_master.run_continous(ptp_cmd_master, timer),
        ssh_slave.run_continous(ptp_cmd_slave, timer),
    ):
        # print(line_m)
        # print(line_s)
        data = __parse_lines(line_s, pattern)
        log_time = 0

        if data:
            # log time is always bigger by one second
            if log_time != 0:
                assert data["ptp4l_runtime"] == log_time + 1

            log_time = data.pop("ptp4l_runtime")

            yield data


def __parse_lines(line, pattern):
    """
    Read floats from line and return parsed dict
    """

    tmp_dict = {}
    nums = []

    matches = re.findall(pattern, line)
    # Squash all signs TODO: error checking if maybe there are two errors next to each other
    for i in range(len(matches)):
        if matches[i] == "+" or matches[i] == "-":
            matches[i + 1] = matches[i] + matches[i + 1]
        else:
            nums.append(float(matches[i]))

    # Expected 4 values (mayber add more)
    if len(nums) == 4:
        for i in range(len(labels)):
            tmp_dict[labels[i]] = nums[i]

        return tmp_dict
