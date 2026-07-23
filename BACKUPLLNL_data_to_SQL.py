#  LLNL weater data API: https://weather.llnl.gov/


import requests
import csv
from datetime import datetime, timedelta
import os
import io
import shutil
import time
import mysql.connector
from mysql.connector import Error
import logging

#===========================================
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

#===========================================
# Function to fetch and process LLNL weather data
def fetch_llnl_weather_data(instrument_id,start_date, end_date):
    formatted_start_date = start_date.strftime('%Y-%m-%d')
    formatted_end_date = end_date.strftime('%Y-%m-%d')

    url = 'https://weather.llnl.gov/cgi-pub/reports/report_export.pl'

    params = {
        'format': 'tsv',
        'instrument_ids': instrument_id,
        'alt_units': '',
        'min': '0',
        'max': '0',
        'avg': '1',
        'data_resolution': 'full',
        'start_date': formatted_start_date,
        'end_date': formatted_end_date
    }
    response = requests.get(url, params=params)

    logging.info(f"Status Code: {response.status_code}")
    logging.info(f"Response Content: {response.text[:100]}")  # Print only the first 100 characters for brevity

    if response.status_code == 200:
        data = []
        reader = csv.DictReader(io.StringIO(response.text), delimiter='\t', fieldnames=['date', 'temperature', 'humidity'])
        next(reader)  # Skip header row
        print("")
        for row in reader:
            if float(row['temperature']) > -10.0:  # Check if 'temperature' is not empty and greater than -10
                data.append({'date': row['date'], 'temperature': float(row['temperature'])})
                #logging.debug(f"{row['date']}, {float(row['temperature'])}")

            else:
                logging.debug(f"Skipping row with empty temperature: {row}")
        return data
    else:
        logging.info(f"Failed to fetch data: HTTP {response.status_code}")
        return None


#==========================================================================
# Main program
#==========================================================================
#

# Ensure log directory exists
os.makedirs("./logs", exist_ok=True)

#===========================================
# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,  # Set the lowest level to DEBUG so all messages are logged
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format of the log messages
    handlers=[
        logging.FileHandler("./logs/LLNL_dat_to_SQL.log"),  # Log to a file
        logging.StreamHandler()  # Also log to the terminal (console)
    ]
)

#===========================================
#  Connect to the MySQL database

db = connect_to_database()
cursor=connection.cursor() 

# Define the date range 
end_date = datetime.today()
start_date = end_date - timedelta(days=1)
logging.info(f"Fetching LLNL weather data from {start_date} to {end_date}") 


sensorlabel = ['LLNL 2m','LLNL 10m','LLNL 23m','LLNL 52m']
sensorid = ['350','351',]    #'353','352']


# Create the base SQL statement
sql = "INSERT INTO `LLNL_data` (`sensorid`,`sensorlabel`, `timestamp`, `temperature`) VALUES "
values = []

for j in range(len(sensorid )): 
     weather_data = fetch_llnl_weather_data(sensorid[j],start_date, end_date)
     
     dates = [datetime.strptime(entry['date'], '%Y-%m-%d %H:%M:%S') for entry in weather_data]
     temperatures = [entry['temperature'] for entry in weather_data] 
     for i in range(len(dates)):       # Construct the values part of the SQL statement
        string = f"('{sensorid[j]}','{sensorlabel[j]}', '{dates[i]}', {temperatures[i]})"
        logging.debug(string)
        values.append(f"('{sensorid[j]}','{sensorlabel[j]}', '{dates[i]}', {temperatures[i]})")
     sql += ", ".join(values) + ";"    # Join all the values into a single string
     
     

cursor.execute(sql)
connection.commit()

cursor.close()
connection.close()







