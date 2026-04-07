import pandas as pd

df = pd.read_csv("processed_data/groundwater_data.csv", low_memory=False)

important_columns = [
    "STATE",
    "DISTRICT",
    "ASSESSMENT UNIT",
    "Rainfall (mm)",
    "Total Geographical Area (ha)",
    "Ground Water Recharge (ham)",
    "Annual Ground water Recharge (ham)",
    "Annual Extractable Ground water Resource (ham)",
    "Ground Water Extraction for all uses (ha.m)",
    "Stage of Ground Water Extraction (%)",
    "Environmental Flows (ham)",
    "Net Annual Ground Water Availability for Future Use (ham)",
    "Total Ground Water Availability in the area (ham)",
    "YEAR"
]

clean_df = df[important_columns]

print(clean_df.head())
print("\nShape:", clean_df.shape)

clean_df.to_csv("processed_data/groundwater_chatbot_dataset.csv", index=False)

print("\nClean dataset saved.")