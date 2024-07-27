import os
import csv
import shutil
import time
import mysql.connector
from mysql.connector import Error
import logging


# Configure logging for flexibility and control
logging.basicConfig(
    filename='/home/uhi/logs/ProcessCSVtoSQL_3.log',
    level=logging.INFO,  # Adjust logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional timestamp format
)

# Define the directory containing the CSV files
sensor_data_dir = "/home/uhi/SensorData"
archive_dir = "/home/uhi/archived_data"

# Function to connect to MySQL database
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='uhi',
            user='uhi',
            password='uhi'
        )
        if connection.is_connected():
            print("Connected to MySQL database")
            logging.info("Connected to MySQL database")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        logging.error(f"Error connecting to MySQL: {e}")
        return None

# Function to insert data into the sensor_data table
def insert_data(cursor, sensorid, timestamp, temperature, humidity):
    insert_query = """INSERT INTO sensor_data (sensorid, timestamp, temperature, humidity)
                      VALUES (%s, %s, %s, %s)
                      ON DUPLICATE KEY UPDATE
                      temperature = VALUES(temperature),
                      humidity = VALUES(humidity)"""
    record = (sensorid, timestamp, temperature, humidity)
    cursor.execute(insert_query, record)

# Function to process each CSV file and insert data into the database
def process_files(connection):
    cursor = connection.cursor()
    for filename in os.listdir(sensor_data_dir):
        if filename.endswith(".csv"):
            file_path = os.path.join(sensor_data_dir, filename)
            
            # Use the full base filename as sensorid
            base_filename = os.path.splitext(filename)[0]
            sensorid = base_filename
            print(f"Processing file: {filename} with sensorid: {sensorid}")
            logging.info(f"Processing file: {filename} with sensorid: {sensorid}")

            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                csvreader = csv.reader(csvfile)
                lines = list(csvreader)
                if len(lines) < 3:
                    print(f"File {filename} does not contain enough data")
                    continue

                # Process each line starting from the third line
                for line in lines[2:]:
                    if len(line) < 3:
                        print(f"Line missing data in {filename} --> length: {len(line)}")
                    else:
                        timestamp = line[0]
                        temperature = float(line[1])
                        humidity = float(line[2])
                        insert_data(cursor, sensorid, timestamp, temperature, humidity)

            # Generate a new filename with sensorid and the current Unix timestamp
            timestamp = int(time.time())
            new_filename = f"{sensorid}_{timestamp}.csv"
            archive_path = os.path.join(archive_dir, new_filename)

            # Move the processed file to the archive directory
            shutil.move(file_path, archive_path)
            print(f"Moved {filename} to {archive_path}")
            logging.info(f"Moved {filename} to {archive_path}")

    connection.commit()
    cursor.close()

# Main function
def main():
    connection = connect_to_database()
    if connection is not None and connection.is_connected():
        process_files(connection)
        connection.close()

if __name__ == "__main__":
    main()
