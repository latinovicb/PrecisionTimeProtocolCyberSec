import os
from logger import log
import pandas as pd
from class_utils import PlotUtils


class PTPCombinedPlotter(PlotUtils):
    def __init__(self, title, labels_units, location, plot_kwargs):
        super().__init__(title, labels_units, location, plot_kwargs)
        self.fig.suptitle(f"ptp4l parsed data -- {title}")

    def update(self, data, line_name):
        self._PlotUtils__update(data, line_name)


def do(directory, selected, labels_units, ts_type="all", protocol="all"):

    csv_files = [
        file for file in os.listdir(directory + "/data") if file.endswith(".csv")
    ]
    if not csv_files:
        log("No CSV files found in the specified directory.")
        return
    plot_kwargs = {"linestyle": "dashdot"}
    combined_plotter = PTPCombinedPlotter(
        f"combined_ts_{ts_type}_{protocol}",
        labels_units.log_data,
        directory,
        plot_kwargs,
    )

    for csv_file in csv_files:
        file_name = csv_file[: csv_file.rfind(".")]
        if file_name in selected:
            if ts_type != "all":
                if ts_type in file_name:
                    pass
                else:
                    continue

            if protocol != "all":
                if protocol in file_name:
                    pass
                else:
                    continue

            file_path = os.path.join(directory + "/data", csv_file)

            df = pd.read_csv(file_path, index_col=0)

            # only stabilized servo data to be compared
            first_index_of_2 = df["servo"].idxmax()
            df.iloc[:first_index_of_2, :-1] = float("nan")

            if protocol == "all":
                log(
                    "------------------------------------------------------------------"
                )
                log(file_name)
                pd.set_option("display.max_rows", None)
                for ptp_info in list(labels_units.log_data.keys())[1:]:
                    data_row = df[ptp_info]
                    mean = data_row.mean()
                    # mean absolute deviation
                    deviation = abs((data_row - mean).mean())
                    log(ptp_info)
                    log("mean value: ", mean)
                    log("mean absolute deviation ", deviation)
                    log("standard deviation ", data_row.std())

            combined_plotter.update(df, file_name)
