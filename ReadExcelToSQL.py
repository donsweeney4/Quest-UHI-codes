
"""
Open connection to google sheets
Open mysql database
Connect to the excel spreadsheet
read a row of the excel table and 
     insert valid rows into database

"""

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
import csv
import re
import shutil
from datetime import datetime  # Import datetime module correctly
import mysql.connector
from mysql.connector import Error
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pandas as pd
import io
import numpy as np
from googleapiclient.http import MediaIoBaseDownload

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

# Configure logging for flexibility and control

#===========================================
logging.basicConfig(
    filename='/home/uhi/logs/ReadExcelToSQL2.log',
    level=logging.DEBUG,  # Adjust logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional timestamp format
)

connection = connect_to_database()

if connection is None:
    exit(1)
cursor = connection.cursor()



# Define the scope
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Add your service account file path
SERVICE_ACCOUNT_FILE = '/home/ubuntu/macro-scion-430418-m6-8786a0c80083.json'

# Authenticate and construct the service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)

# File ID of the Excel file on Google Drive
FILE_ID = '1W7TP01gA4eWDeukHTwc8lMq4dYt5qTfg'

# Request the file from Google Drive

request = service.files().get_media(fileId=FILE_ID)
file = io.BytesIO()
downloader = MediaIoBaseDownload(file, request)
done = False
while done is False:
    status, done = downloader.next_chunk()

# Move the file pointer to the beginning
file.seek(0)

# Read the file into a pandas DataFrame
df = pd.read_excel(file)

#===========================================()
 
num_rows = df.shape[0]  
print(f"\n number of rows in dataframe {num_rows} \n")
for jj in range(num_rows):
    if pd.notna(df.iloc[jj, 2]) and re.fullmatch(r'\d+[a-zA-Z]?', str(df.iloc[jj, 2]).strip()) and isinstance(df.iloc[jj, 3], str):
        sensor_id = df.iloc[jj,2]
        sensor_name = df.iloc[jj,3]

        current_latitude = df.iloc[jj,4]
        if not (isinstance(current_latitude, float) and not np.isnan(current_latitude)):
            current_latitude = 0.0

        current_longitude = df.iloc[jj,5]
        if not (isinstance(current_longitude, float) and not np.isnan(current_longitude)):
            current_longitude = 0.0

        owners_first_name = df.iloc[jj,12]
        if not isinstance(owners_first_name, str):
            owners_first_name = None

        date_value = df.iloc[jj,9]
        if isinstance(date_value, (pd.Timestamp, datetime)):
            date_installed = date_value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_installed = None

        logging.debug(f"Row {jj} Sensor ID: {sensor_id},  Sensor Name: {sensor_name}, {current_latitude},  {current_longitude}, {owners_first_name}, {date_installed}")

        # Generate the current timestamp
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        insert_query = """INSERT INTO meta_data (
            timestamp, 
            sensor_id, 
            sensor_name,
            current_latitude,
            current_longitude,
            owners_first_name,
            date_installed
        )
        VALUES(%s, %s, %s, %s, %s, %s, %s)"""

        record =       (current_timestamp,
                        sensor_id,
                        sensor_name,
                        current_latitude,
                        current_longitude,
                        owners_first_name,
                        date_installed
                        )

        logging.debug(record)
        cursor.execute(insert_query, record)

connection.commit()

cursor.execute("SELECT * FROM latest_sensor_meta_data")
columns = [desc[0] for desc in cursor.description]
rows = cursor.fetchall()
print("\n\n=================================================")
print(f"latest_sensor_meta_data ({len(rows)} rows):")
print(columns)
for row in rows:
    print(row)

cursor.close()