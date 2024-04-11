import os
import pandas as pd
import matplotlib.pyplot as plt
from class_utils import PlotUtils


class PTPCombinedPlotter(PlotUtils):
    def __init__(self, title, labels_units, location, plot_kwargs):
        super().__init__(title, labels_units, location, plot_kwargs)
        self.fig.suptitle(f"ptp4l parsed data -- {title}")

    def update(self, data, line_name):
        self._PlotUtils__update(data, line_name)


def do(directory, selected, labels_units):

    csv_files = [file for file in os.listdir(directory) if file.endswith('.csv')]
    if not csv_files:
        print("No CSV files found in the specified directory.")
        return
    plot_kwargs = {'linestyle':'solid'}
    combined_plotter = PTPCombinedPlotter("combined_all",labels_units.log_data,directory, plot_kwargs)

    for csv_file in csv_files:
        file_name = csv_file[:csv_file.rfind('.')]
        if file_name in selected:
            file_path = os.path.join(directory, csv_file)

            df = pd.read_csv(file_path, index_col=0)

            combined_plotter.update(df, file_name)
