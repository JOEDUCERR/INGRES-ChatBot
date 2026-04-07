import pandas as pd

file_path = "data/raw_excel/2024_25.xlsx"

# skip metadata rows
df = pd.read_excel(file_path, skiprows=7)

# remove rows where STATE is NaN
df = df[df["STATE"].notna()]

# reset index
df = df.reset_index(drop=True)

print("Columns:")
print(df.columns)

print("\nFirst rows:")
print(df.head())

print("\nShape:")
print(df.shape)