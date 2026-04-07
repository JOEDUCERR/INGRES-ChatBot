import pandas as pd
import sqlite3

# load cleaned dataset
df = pd.read_csv("processed_data/groundwater_chatbot_dataset.csv")

# connect to SQLite database
conn = sqlite3.connect("groundwater.db")

# save dataframe as SQL table
df.to_sql("groundwater", conn, if_exists="replace", index=False)

print("Database created successfully.")

# check number of rows
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM groundwater")

print("Rows in database:", cursor.fetchone()[0])

conn.close()