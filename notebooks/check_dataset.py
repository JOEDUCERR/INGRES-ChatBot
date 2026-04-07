import pandas as pd

df = pd.read_csv("processed_data/groundwater_data.csv", low_memory=False)

for col in df.columns:
    print(col)