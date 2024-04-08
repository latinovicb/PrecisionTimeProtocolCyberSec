import pandas as pd
import re
import matplotlib
import matplotlib.pyplot as plt

# TODO: add functions for statistics creation
# TODO: additionally write plot data to csv -
# so they could be compared between each other


class PlotSaver:
    def __init__(self, title, labels_units, location, save_period):
        self.location = location
        self.title = title
        self.labels_units = labels_units
        self.save_period = save_period
        self.csv_mode = "x"
        self.fig, self.axs = plt.subplots(3, figsize=(16, 9), dpi=200)
        self.fig.suptitle(f"ptp4l parsed data -- {title}")
        # plt.rcParams["figure.figsize"] = [12.04, 7.68]
        plt.ion()

    def update(self, data):
        for i in range(len(self.labels_units.keys()) - 1):
            self.__plot_next(
                self.axs[i],
                list(self.labels_units.keys())[i + 1],
                list(self.labels_units.values())[i + 1],
                data,
            )

        # self.fig.canvas.draw()
        self.__save_fig()
        self.__save_csv(data)

    def __plot_next(self, ax, name, unit, data):
        ax.title.set_text(name)
        ax.set(ylabel=unit)
        ax.plot(data[name], label=name, linestyle=(0, (1, 10)), color="blue")

    def __save_fig(self):
        name = f"{self.location}/ptp_data_{self.title}"
        print(f"Figure updated/saved to {name}")
        plt.savefig(name)

    def __save_csv(self, data):
        name = f"{self.location}/csv_data_{self.title}.csv"
        try:
            data.to_csv(name, mode=self.csv_mode, header=False)
        except FileExistsError as e:
            print(e, f" ... rewriting file {name}")
            data.to_csv(name, mode="w")
            self.csv_mode = "a"


def do(ssh_master, scp_master, ssh_slave, scp_slave, cmds, mode):
    """
    Read lines from ptp4l output
    """
    ### Perm vars -- will not likely change
    labels_units = {
        "ptp4l_runtime": "time [s]",
        "master_offset": "time [ns]",
        "servo_freq": "freq [ppb]",
        "path_delay": "time [ns]",
    }  # ptp4l_runtime used just for log consitecny verification
    pattern = r"(?:\b[+\-]?\d+(?:\.\d+)?\b\s*(?![-+])|[+\-])"
    ###

    title = mode
    ptp_cmd_master = cmds[mode]["master"]
    ptp_cmd_slave = cmds[mode]["slave"]

    ### Tmp vars -- should be taken as an arguments from main
    timer = 60
    buff_size = 10
    location = "/tmp"
    save_period = 1
    ###
    print(
        "Running ptp reader with the following info: \n",
        "master: ",
        ptp_cmd_master,
        "\n",
        "slave: ",
        ptp_cmd_slave,
        "\n",
        "plot buff size: ",
        buff_size,
        "\n",
        "timer: ",
        timer,
        "\n",
        " ... initializing",
    )

    count = 0
    first_indx = 0
    labels = list(labels_units.keys())
    myPlt = PlotSaver(title, labels_units, location, save_period)
    df = pd.DataFrame(
        columns=labels[1:],
    )

    for data in __run_sync(
        ssh_master, ssh_slave, ptp_cmd_master, ptp_cmd_slave, timer, labels, pattern
    ):
        # Fill by buff to ease the load
        if count == buff_size:
            print("Passing data to plotter\n", df)
            myPlt.update(df)
            first_indx += count
            df = pd.DataFrame(
                columns=labels[1:],
            )
            count = 0

        data = pd.Series(
            data, name=first_indx + count
        )  # NOTE: probably not vert resource efficient
        df = df._append(data)  # FIXME: should be changed to concat
        count += 1


def __run_sync(
    ssh_master, ssh_slave, ptp_cmd_master, ptp_cmd_slave, timer, labels, pattern
):
    """
    Run sync between server and master and return numbers which were parsed line by line
    """
    for line_m, line_s in zip(
        ssh_master.run_continous(ptp_cmd_master, timer),
        ssh_slave.run_continous(ptp_cmd_slave, timer),
    ):
        # print(line_m)
        # print(line_s)
        data = __parse_lines(line_s, pattern, labels)
        log_time = 0

        if data:
            # log time is always bigger by one second
            if log_time != 0:
                assert data["ptp4l_runtime"] == log_time + 1

            log_time = data.pop("ptp4l_runtime")

            yield data


def __parse_lines(line, pattern, labels):
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

    # Expected same number of values as existing labels
    if len(nums) == len(labels):
        for i in range(len(labels)):
            tmp_dict[labels[i]] = nums[i]

        return tmp_dict
