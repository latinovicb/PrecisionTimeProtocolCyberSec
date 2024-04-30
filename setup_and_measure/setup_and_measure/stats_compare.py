import os
import random
import numpy as np
import scipy as sci
from logger import log
import pandas as pd
from class_utils import PlotUtils
import matplotlib.pyplot as plt

stat_names = ["mean", "median", "median - mean", "variance", "standard deviation",
              "absolute mean deviation", "absolute median deviation"]


class PTPCombinedPlotter(PlotUtils):
    def __init__(self, title, labels_units, location, plot_kwargs):
        super().__init__(title, labels_units, location, plot_kwargs)
        self.fig.suptitle(f"ptp4l parsed data -- {title}")

    def update(self, data, line_name):
        self._PlotUtils__update(data, line_name)


def stat_maker(data_row, ptp_info, name):
    data_row = data_row[~np.isnan(data_row)]

    mean = np.mean(data_row)
    median = np.median(data_row)
    mean_v_median = mean - median
    variance = np.var(data_row)
    standard_deviation = np.std(data_row)
    mean_abs_deviation = np.mean(np.absolute(data_row - mean))
    median_abs_deviation = sci.stats.median_abs_deviation(data_row)
    fourier_trans = np.fft.fft(data_row)

    data_series = pd.Series(
        [mean, median, mean_v_median, variance, standard_deviation,
            mean_abs_deviation, median_abs_deviation], stat_names, name=name
    )

    # add median
    # mean - median

    # numpy short time fft, fft numpy, clustering

    return data_series


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

    if protocol == "all" and ts_type == "all":  # do this only once
        stats_data_frames = {}

        need_stats = list(labels_units.log_data.keys())[1:]
        for stat in need_stats:
            stats_data_frames[stat] = pd.DataFrame(index=stat_names)

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
            # NOTE: only data where the servo is already stabilized taken into account
            first_index_of_2 = df["servo"].idxmax()
            df.iloc[:first_index_of_2, :-1] = float("nan")

            if protocol == "all" and ts_type == "all":
                for ptp_info in need_stats:
                    data_row = df[ptp_info].to_numpy()
                    data = stat_maker(data_row, ptp_info, file_name)
                    assert len(data) == len(stat_names)
                    stats_data_frames[ptp_info][data.name] = data

            combined_plotter.update(df, file_name)

    if protocol == "all" and ts_type == "all":  # do this only once
        for i in stats_data_frames.keys():
            stat_data = stats_data_frames[i]
            dest = directory + "/data/" + i + "_statistics.csv"
            stat_data.to_csv(dest, mode='w')
            log(f"Statistics for {i} saved to {dest}")
