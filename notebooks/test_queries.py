import sqlite3

conn = sqlite3.connect("groundwater.db")

cursor = conn.cursor()

query = """
SELECT STATE,
MAX("Total Ground Water Availability in the area (ham)")
FROM groundwater
GROUP BY STATE
LIMIT 10
"""

cursor.execute(query)

for row in cursor.fetchall():
    print(row)

conn.close()