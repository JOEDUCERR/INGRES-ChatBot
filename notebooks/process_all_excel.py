import pandas as pd
import os

# folder containing raw excel files
folder_path = "data/raw_excel"

all_data = []

files = os.listdir(folder_path)

print("Files found:", files)

for file in files:

    if file.endswith(".xlsx"):

        file_path = os.path.join(folder_path, file)

        print("\nProcessing:", file)

        # read excel
        df = pd.read_excel(file_path, skiprows=7)

        # remove rows without state
        df = df[df["STATE"].notna()]

        # reset index
        df = df.reset_index(drop=True)

        # extract year from filename
        year = file.replace(".xlsx", "")

        # add year column
        df["YEAR"] = year

        all_data.append(df)

# combine all data
final_df = pd.concat(all_data, ignore_index=True)

print("\nFinal dataset shape:", final_df.shape)

# save cleaned dataset
output_path = "processed_data/groundwater_data.csv"

final_df.to_csv(output_path, index=False)

print("\nDataset saved to:", output_path)