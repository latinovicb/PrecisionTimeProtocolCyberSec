import pandas as pd
import matplotlib.pyplot as plt
from logger import log
import re
from class_utils import PTPSinglePlotter
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)


class PtpReader:
    def __init__(
        self,
        ssh_master,
        scp_master,
        ssh_slave,
        scp_slave,
        cmds,
        log_config,
        label_pattern,
        remote_dir,
    ):
        self.ssh_master = ssh_master
        self.scp_master = scp_master
        self.ssh_slave = ssh_slave
        self.scp_slave = scp_slave
        self.cmds = cmds

        self.labels_units = label_pattern.log_data
        self.pattern = label_pattern.re_pattern  # for getting numerical values
        self.servo_state_pattern = r"\b(s\d+)\b"
        self.servo_states = {"s0", "s1", "s2"}
        self.labels = list(self.labels_units.keys())

        self.timer = log_config.time
        self.buff_size = log_config.buff_size
        self.location = log_config.location

        self.remote_dir = remote_dir

    def do(self, mode):
        if mode not in self.cmds:
            log(f"'{mode}' mode is not defined!")

        ptp_cmd_master = self.cmds[mode]["master"]
        ptp_cmd_slave = self.cmds[mode]["slave"]

        log(
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

        iface_cap = re.search(r"-i\s+(\S+)", ptp_cmd_slave).group(1)
        # captured directly on interface specified for ptp4l -- pacekts can be read without encryption
        # captured only on slave -- should not be saved to /tmp as not to increase ram usage
        pcap_remote = f"/{self.remote_dir}/{mode}.pcap"

        # TODO: this call is blocking and killed only by the timeout in ssh class
        self.ssh_slave.run_command(
            f"tshark -i {iface_cap} -w {pcap_remote}")

        assert (self.ssh_slave.run_command(
            "ps aux | grep tshark | grep -v grep"
        ))

        try:
            self.__start(mode, ptp_cmd_master, ptp_cmd_slave)
        except Exception as e:
            raise e
        finally:
            self.ssh_slave.run_command("killall tshark")
            self.scp_slave.get(
                f"{pcap_remote}", f"{self.location.caps}{mode}.pcap")
            self.ssh_slave.run_command(f"rm {pcap_remote}")

    def __start(self, mode, ptp_cmd_master, ptp_cmd_slave):
        """
        Read lines from ptp4l output
        """

        count = 0
        first_indx = 0
        plot_style = (0, (5, 10))
        plot_kwargs = {"linestyle": plot_style, "color": "blue"}
        myPlt = PTPSinglePlotter(
            mode, self.labels_units, self.location, plot_kwargs)
        df = pd.DataFrame(
            columns=self.labels[1:],
        )

        try:
            for data in self.__run_sync(
                ptp_cmd_master,
                ptp_cmd_slave,
            ):
                # Fill by buff to ease the load
                if count == self.buff_size:
                    # log("Passing data to plotter\n", df)
                    myPlt.update(df)
                    first_indx += count
                    df = pd.DataFrame(
                        columns=self.labels[1:],
                    )
                    count = 0

                # NOTE: probably not very resource efficient
                data = pd.Series(data, name=first_indx + count)
                df = pd.concat([df, data.to_frame().T], axis=0)
                count += 1
        except Exception as e:
            raise e
        finally:
            myPlt.show_mean()

    def __run_sync(self, ptp_cmd_master, ptp_cmd_slave):
        """
        Run sync between server and master and return numbers which were parsed line by line
        """
        for line_m, line_s in zip(
            self.ssh_master.run_continous(ptp_cmd_master, self.timer),
            self.ssh_slave.run_continous(ptp_cmd_slave, self.timer),
        ):
            data = self.__parse_lines(line_s)
            log_time = 0

            # log time always bigger by one
            if data:
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
        if servo_state := list(self.servo_states & set(matches)):
            assert len(servo_state) == 1
            servo_state = servo_state[0]
            matches.remove(servo_state)
            for i in range(len(matches)):
                if matches[i] == "+" or matches[i] == "-":
                    matches[i + 1] = matches[i] + matches[i + 1]
                else:
                    nums.append(float(matches[i]))

            nums.append(int(servo_state[-1]))
            # Expected same number of values as existing labels
            if len(nums) == len(self.labels):
                for i in range(len(self.labels)):
                    tmp_dict[self.labels[i]] = nums[i]

                return tmp_dict
        else:
            log(line)
