import os
import numpy as np
import scipy as sci
from logger import log
import pandas as pd
from class_utils import PlotUtils

stat_names = ["mean", "median", "median - mean", "variance", "standard deviation",
              "absolute mean deviation", "absolute median deviation"]


class PTPCombinedPlotter(PlotUtils):
    def __init__(self, title, labels_units, location, plot_kwargs):
        super().__init__(title, labels_units, location, plot_kwargs)
        self.fig.suptitle(f"ptp4l data -- {title}")

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
        self._PlotUtils__save_fig(self.location.stats)

    def __plot_hist(self, data, ax, name, unit, line_name=None):
        ax.title.set_text(name)
        ax.set(ylabel=unit)
        ax.hist(data[name], bins=100)

        if line_name is not None:
            ax.legend()


def stat_maker(data_row, ptp_info, name):
    data_row = data_row[~np.isnan(data_row)]

    mean = np.mean(data_row)
    median = np.median(data_row)
    mean_v_median = mean - median
    variance = np.var(data_row)
    standard_deviation = np.std(data_row)
    mean_abs_deviation = np.mean(np.absolute(data_row - mean))
    median_abs_deviation = sci.stats.median_abs_deviation(data_row)

    # TODO: finish fft & spectral analysis
    # histogram = np.histogram(data_row, bins=10)
    # fast_ft = sci.fft.fft(data_row)
    # fft_magnitude = np.abs(fast_ft)
    # slow_ft = sci.signal.stft(data_row) #NOTE: nperseg = 256 is greater than input length

    data_series = pd.Series(
        [mean, median, mean_v_median, variance, standard_deviation,
            mean_abs_deviation, median_abs_deviation], stat_names, name=name
    )

    # add median
    # mean - median

    # numpy short time fft, fft numpy, clustering

    return data_series


class StatMakerComparator:
    def __init__(self, location, selected, labels_units):
        self.location = location
        self.selected = selected
        self.labels_units = labels_units

    def do(self, ts_type="all", protocol="all", do_stats=False):

        csv_files = [
            file for file in os.listdir(self.location.data) if file.endswith(".csv")
        ]
        if not csv_files:
            log(
                f"No CSV files found in the specified location. {self.location.data}")
            return
        plot_kwargs = {"linestyle": "dashdot"}
        combined_plotter = PTPCombinedPlotter(
            f"combined_ts_{ts_type}_{protocol}",
            self.labels_units.log_data,
            self.location,
            plot_kwargs,
        )

        if do_stats:
            stats_data_frames = {}

            need_stats = list(self.labels_units.log_data.keys())[1:]
            for stat in need_stats:
                stats_data_frames[stat] = pd.DataFrame(index=stat_names)

        for csv_file in csv_files:
            file_name = csv_file[: csv_file.rfind(".")]
            if file_name in self.selected:

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

                file_path = os.path.join(self.location.data, csv_file)
                df = pd.read_csv(file_path, index_col=0)

                # NOTE: only data where the servo is already stabilized taken into account for statistical analysis
                first_index_of_2 = df["servo"].idxmax()
                df.iloc[:first_index_of_2, :-1] = float("nan")

                if do_stats:
                    # stat_plots = location.stats + file_name + "_stat_plots"
                    # if not os.path.exists(stat_plots):
                    #     os.makedirs(stat_plots)
                    stat_plotter = PTPCombinedPlotter(
                        f"histogram_{file_name}",
                        self.labels_units.log_data,
                        self.location,
                        plot_kwargs,
                    )
                    stat_plotter.make_hist(df)
                    for ptp_info in need_stats:
                        data_row = df[ptp_info].to_numpy()
                        data = stat_maker(data_row, ptp_info, file_name)
                        assert len(data) == len(stat_names)
                        stats_data_frames[ptp_info][data.name] = data
                else:
                    combined_plotter.update(df, file_name)

        if do_stats:
            for i in stats_data_frames.keys():
                stat_data = stats_data_frames[i]
                dest = self.location.stats + i + "_statistics_all.csv"
                stat_data.to_csv(dest, mode='w')
                log(f"Statistics for {i} saved to {dest}")
