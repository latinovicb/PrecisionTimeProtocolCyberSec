import os
import pandas as pd
import matplotlib.pyplot as plt


def do(directory, labels):
    csv_files = [file for file in os.listdir(directory) if file.endswith('.csv')]

    if not csv_files:
        print("No CSV files found in the specified directory.")
        return

    fig, ax = plt.subplots(3,figsize=(16, 9), dpi=200)

    for csv_file in csv_files:
        file_path = os.path.join(directory, csv_file)

        df = pd.read_csv(file_path, index_col=0)

        csv_file = csv_file[:csv_file.rfind('.')]

        ax[0].plot(df['master_offset'], label=csv_file)
        ax[1].plot(df['servo_freq'], label=csv_file)
        ax[2].plot(df['path_delay'], label=csv_file)

#     ax.set_title('CSV Files Plot')
#     ax.set_xlabel('X-axis')
#     ax.set_ylabel('Y-axis')

    ax[0].legend()

#     # Show the plot
    plt.savefig(directory + "/combined_all")
