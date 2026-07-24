import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
import mysql.connector

# Connect to the MySQL database
db = mysql.connector.connect(
    host=os.environ['DB_HOST'],
    database='uhi',
    user=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD']
)

if db.is_connected():
    print("Connected to MySQL database")
else:
    print("Error Connecting to MySQL database")

cursor = db.cursor()

# Step 1: Drop the latest_sensor_meta_data table if it exists
cursor.execute("DROP TABLE IF EXISTS latest_sensor_meta_data")
print("Step 1: Dropped latest_sensor_meta_data table (if it existed)")

# Step 2: Create latest_sensor_meta_data table with the same structure as meta_data
cursor.execute("CREATE TABLE latest_sensor_meta_data LIKE meta_data")
print("Step 2: Created latest_sensor_meta_data table with structure of meta_data")

# Step 3: Get distinct sensor_id values
cursor.execute("SELECT DISTINCT sensor_id FROM meta_data")
sensor_ids = cursor.fetchall()
print(f"Step 3: Found {len(sensor_ids)} distinct sensor_id values: {[s[0] for s in sensor_ids]}")

# Get column names from meta_data
cursor.execute("SHOW COLUMNS FROM meta_data")
columns = cursor.fetchall()
column_names = [column[0] for column in columns]
print(f"Step 3b: meta_data columns ({len(column_names)}): {column_names}")

# Step 4: Find the newest row for each distinct sensor_id
newest_rows = []
for sensor in sensor_ids:
    sensor_id = sensor[0]
    cursor.execute("""
    SELECT t1.*
    FROM meta_data t1
    INNER JOIN (
        SELECT sensor_id, MAX(timestamp) AS latest_timestamp
        FROM meta_data
        WHERE sensor_id = %s
        GROUP BY sensor_id
    ) t2 ON t1.sensor_id = t2.sensor_id AND t1.timestamp = t2.latest_timestamp
    """, (sensor_id,))
    result = cursor.fetchone()
    if result:
        newest_rows.append(result)
        print(f"Step 4: sensor_id={sensor_id} -> newest row: {result}")
    else:
        print(f"Step 4: sensor_id={sensor_id} -> no row found")
print(f"Step 4: Collected {len(newest_rows)} newest rows out of {len(sensor_ids)} sensor_ids")

# Step 5: Insert the newest row for each distinct sensor_id into the latest_sensor_meta_data table
for row in newest_rows:
    placeholders = ', '.join(['%s'] * len(row))
    columns = ', '.join(column_names)
    insert_query = f"INSERT INTO latest_sensor_meta_data ({columns}) VALUES ({placeholders})"
    cursor.execute(insert_query, row)
    print(f"Step 5: Inserted row for sensor_id={row[column_names.index('sensor_id')]}")
print(f"Step 5: Inserted {len(newest_rows)} rows into latest_sensor_meta_data")

# Commit the transaction
db.commit()
print("Step 6: Transaction committed")

# Close the cursor and connection
cursor.close()
db.close()
print("Step 7: Cursor and connection closed")
