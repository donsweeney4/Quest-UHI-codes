import requests
import csv
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
import io
import mysql.connector
from mysql.connector import Error
import logging

# Function to connect to MySQL database
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host=os.environ['DB_HOST'],
            database='uhi',
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )
        if connection.is_connected():
            print("Connected to MySQL database")
            logging.info("Connected to MySQL database")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        logging.error(f"Error connecting to MySQL: {e}")
        return None

# Function to fetch and process LLNL weather data
def fetch_llnl_weather_data(height, start_date, end_date):
    formatted_start_date = start_date.strftime('%Y-%m-%d')
    formatted_end_date = end_date.strftime('%Y-%m-%d')

    url = 'https://weather.llnl.gov/api/report/simple/'

    params = {
        'start_date': formatted_start_date,
        'end_date': formatted_end_date,
        'schema': 'grid',
        'tower_id': '200',  # LLNL main site (Site 300 is '301')
        'height': height,
        'instrument_type': 'temperature',
    }
    response = requests.get(url, params=params, timeout=30)

    logging.info(f"Status Code: {response.status_code}")
    logging.info(f"Response Content: {response.text[:200]}")

    if response.status_code != 200:
        logging.info(f"Failed to fetch data: HTTP {response.status_code}")
        return None

    payload = response.json()
    field_name = f"Air_Temperature_celsius_LLNL_{height}m"
    data = []
    for row in payload.get('data', []):
        temperature = row.get(field_name)
        if temperature is not None and float(temperature) > -10.0:
            data.append({'date': row['Datetime_PST_Standard'], 'temperature': float(temperature)})
        else:
            logging.debug(f"Skipping row with empty/invalid temperature: {row}")
    return data

# Ensure log directory exists
os.makedirs("./logs", exist_ok=True)

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("./logs/LLNL_dat_to_SQL.log"),
        logging.StreamHandler()
    ]
)

# Connect to the MySQL database
connection = connect_to_database()
if connection:
    cursor = connection.cursor()

    # Define the date range
    end_date = datetime.today() 
    start_date = end_date - timedelta(hours=2)

    logging.info(f"Fetching LLNL weather data from {start_date} to {end_date}")

    sensorlabel = ['LLNL (2m)', 'LLNL (10m)', 'LLNL (23m)', 'LLNL (52m)']
    sensorid = ['Sensor52a', 'Sensor52b', 'Sensor52c', 'Sensor52d']
    height = ['2', '10', '23', '52']
    sql = """INSERT INTO `LLNL_data` (`sensorid`, `sensorlabel`, `timestamp`, `temperature`) VALUES """
    values = []

    for j in range(len(height)):
        weather_data = fetch_llnl_weather_data(height[j], start_date, end_date)

        if not weather_data:
            logging.error(f"No data returned for sensor {sensorid[j]}")
            continue

        dates = [datetime.strptime(entry['date'], '%Y-%m-%dT%H:%M:%S') for entry in weather_data]
        temperatures = [entry['temperature'] for entry in weather_data]

        for i in range(len(dates)):
            string = f"('{sensorid[j]}', '{sensorlabel[j]}', '{dates[i]}', {temperatures[i]})"
            values.append(string)

    if values:  # Execute only if there are values to insert
        sql += ", ".join(values) # Join all values into a single string
        sql += """
                ON DUPLICATE KEY UPDATE 
                sensorlabel = VALUES(sensorlabel), 
                temperature = VALUES(temperature);
              """
        #logging.debug(f"Final SQL Query: {sql}")
        try:
            cursor.execute(sql)
            #logging.debug(f"Inserted {cursor.rowcount} rows")
        except Error as e:
            logging.error(f"Error executing SQL: {e}")

    connection.commit()

    # Close resources
    cursor.close()
    connection.close()
