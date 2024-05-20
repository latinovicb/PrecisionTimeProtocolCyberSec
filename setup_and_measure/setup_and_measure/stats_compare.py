import os
import numpy as np
import scipy as sci
import scipy.stats as stats
from logger import log
import pandas as pd
from class_utils import PTPCombinedPlotter, packets_time_delta

stat_names = ["mean", "median", "mean - median",
              "abs. mean dev.", "abs. median dev.",
              "standard dev.", "variance",
              "spike prob. (Z-score) [\%]", "spike prob. (IQR) [\%]"]

iqr_multiplier = 3.5
z_threshold = 3


def stat_maker(data_row, ptp_info, name, unit):
    data_row = data_row[~np.isnan(data_row)]

    mean = np.mean(data_row)
    median = np.median(data_row)
    mean_v_median = mean - median
    variance = np.var(data_row)
    standard_deviation = np.std(data_row)
    mean_abs_deviation = np.mean(np.absolute(data_row - mean))
    median_abs_deviation = sci.stats.median_abs_deviation(data_row)

    z_score = stats.zscore(data_row)
    # data_with_z_scores = list(zip(data_row, z_score))
    # counter1 = 0
    # for value, scor in data_with_z_scores:
    #     if abs(scor) > 3:
    #         print(counter1, " ", value, " ", scor)
    #         counter1 += 1
    # assert round(spike_percentage/100, 6) == round(probability_of_spikes, 6)
    is_spike = np.absolute(z_score) > z_threshold
    spike_percentage_z = (len([i for i in is_spike if i])/len(data_row))*100
    probability_of_spikes_z = np.mean(is_spike)

    Q1 = np.percentile(data_row, 25)
    Q3 = np.percentile(data_row, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - iqr_multiplier * IQR
    upper_bound = Q3 + iqr_multiplier * IQR
    outliers = data_row[(data_row < lower_bound) | (data_row > upper_bound)]
    probability_of_spikes_irq = len(outliers) / len(data_row)

    # spike_percentage_irq = len(outliers)/len(data_row)*100

    my_names = [name + f" [{unit}]" for name in stat_names[:-3]]
    left_ones = stat_names[-3:]
    left_ones[0] = left_ones[0] + f" [{unit}^2]"

    data_series = pd.Series(
        [mean, median, mean_v_median,
         mean_abs_deviation, median_abs_deviation,
         standard_deviation, variance,
         probability_of_spikes_z * 100, probability_of_spikes_irq * 100], my_names + left_ones, name=name
    )
    return data_series


class StatMakerComparator:
    def __init__(self, location, selected, labels_units):
        self.location = location
        self.selected = selected
        self.labels_units = labels_units

    def do(self, ts_type="all", protocol="all", do_stats=False, do_packets=False):

        csv_files = [
            file for file in os.listdir(self.location.data) if file.endswith(".csv")
        ]
        if not csv_files:
            log(
                f"No CSV files found in the specified location. {self.location.data}")
            return
        plot_kwargs = {"linestyle": "dashdot"}

        if do_stats:
            stats_data_frames = {}

            need_stats = list(self.labels_units.log_data.keys())[1:]
            for stat in need_stats:
                stats_data_frames[stat] = pd.DataFrame()
        else:
            combined_plotter = PTPCombinedPlotter(
                f"combined_ts_{ts_type}_{protocol}",
                self.labels_units.log_data,
                self.location,
                plot_kwargs,
            )

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
                # for the purpose of data comparison & analysis remove n more samples, just to be sure
                nan_vals_after_stable_servo = 20
                columns_to_nan = df.columns.difference(['servo'])
                first_index = df[df['servo'] == 2.0].index[0]
                df.loc[:first_index, columns_to_nan] = np.nan
                last_index = min(
                    first_index + nan_vals_after_stable_servo, len(df))
                df.loc[first_index:last_index, columns_to_nan] = np.nan

                if do_packets:
                    packets_time_delta(file_name, self.location,
                                       nan_vals_after_stable_servo + 20,
                                       plot_kwargs)
                if do_stats:
                    no_servo_labels = self.labels_units.log_data.copy()
                    no_servo_labels.pop('servo')

                    stat_plotter = PTPCombinedPlotter(
                        f"{file_name}_hist_rice",
                        no_servo_labels,
                        self.location,
                        plot_kwargs,
                    )
                    stat_plotter.make_hist(df)
                    del stat_plotter

                    stat_plotter = PTPCombinedPlotter(
                        f"{file_name}_iqr_{iqr_multiplier}",
                        no_servo_labels,
                        self.location,
                        plot_kwargs,
                    )
                    stat_plotter.make_box(df)
                    del stat_plotter

                    for ptp_info in need_stats:
                        data_row = df[ptp_info].to_numpy()
                        data = stat_maker(data_row, ptp_info,
                                          file_name, self.labels_units.log_data[ptp_info])
                        assert len(data) == len(stat_names)
                        stats_data_frames[ptp_info][data.name] = data
                else:
                    # can't be plotted at the same time as histogram due to interactive plotting process issues
                    combined_plotter.update(df, file_name)

        if do_stats:
            for i in stats_data_frames.keys():
                stat_data = stats_data_frames[i]
                dest = self.location.csv + i + f"_statistics_{ts_type}.csv"
                stat_data.to_csv(dest, mode='w')
                log(f"Statistics for {i} saved to {dest}")
