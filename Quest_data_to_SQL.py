import requests
import csv
from datetime import datetime, timedelta
import os
import io
import mysql.connector
from mysql.connector import Error
import logging

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


#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Function to fetch and process LLNL weather data
def fetch_quest_weather_data(instrument_id, start_date, end_date):
    formatted_start_date = start_date.strftime('%Y-%m-%d')
    formatted_end_date = end_date.strftime('%Y-%m-%d')

#############################################################################

        # Fetch Quest Weather Station data asynchronously
        async with aiohttp.ClientSession() as session:
            tasks = []
            for start_timestamp, end_timestamp in generate_timestamps(days_ago , datetime.now()):
                tasks.append(fetch_QuestWeatherStation_data(session, start_timestamp, end_timestamp))

            responses = await asyncio.gather(*tasks)

        # Process Quest Weather Station data
        temperatures_api = []
        timestamps_api = []
        windspeed_api = []
        for data in responses:
            if data and 'sensors' in data:
                for sensor in data['sensors']:
                    for record in sensor['data']:
                        if 'temp_out' in record and 'ts' in record:
                            temperatures_api.append((record['temp_out'] - 32) / 1.8)
                            windspeed_api.append(record['wind_speed_avg'])
                            timestamps_api.append(datetime.fromtimestamp(record['ts']))

        # Debug output
        logger.debug(f"First few timestamps_api: {timestamps_api[:5]}")
        logger.debug(f"First few temperatures_api: {temperatures_api[:5]}")
        logger.debug(f"First few windspeed_api: {windspeed_api[:5]}")

        if not temperatures_api or not timestamps_api:
            logger.warning("No Quest Weather Station data found.")
        else:
            logger.debug(f"Quest Weather Station data: {len(temperatures_api)} records found.")

        # Add Quest Weather Station data to the traces
        if temperatures_api and timestamps_api:
            trace_quest_celsius = go.Scatter(
                x=timestamps_api,
                y=temperatures_api,
                mode='lines',
                name='Sensor51 (Quest Weather Station)'
            )
            traces_celsius.append(trace_quest_celsius)

            trace_quest_fahrenheit = go.Scatter(
                x=timestamps_api,
                y=[temp * 9/5 + 32 for temp in temperatures_api],
                mode='lines',
                name='Quest Weather Station'
            )
            traces_fahrenheit.append(trace_quest_fahrenheit)

            # Make the windspeed trace not visible on load
            trace_quest_windspeed = go.Scatter(
                x=timestamps_api,
                y=windspeed_api,
                mode='lines',
                name='Sensor51 (Quest Wind Speed)',
                yaxis='y2',  # Use secondary y-axis
                visible='legendonly'  # Start as hidden
            )
            traces_windspeed.append(trace_quest_windspeed)

            logger.debug("Quest Weather Station data added to traces.")
        else:
            logger.warning("Quest Weather Station data not added to traces due to missing data.")


"""
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
    logging.info(f"Response Content: {response.text[:100]}")

    if response.status_code == 200:
        data = []
        reader = csv.DictReader(io.StringIO(response.text), delimiter='\t', fieldnames=['date', 'temperature', 'humidity'])
        next(reader)  # Skip header row
        for row in reader:
            if float(row['temperature']) > -10.0:
                data.append({'date': row['date'], 'temperature': float(row['temperature'])})
            else:
                logging.debug(f"Skipping row with empty temperature: {row}")
        return data
    else:
        logging.info(f"Failed to fetch data: HTTP {response.status_code}")
        return None
"""
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


# Ensure log directory exists
os.makedirs("./logs", exist_ok=True)

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("./logs/quest_dat_to_SQL.log"),
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

    logging.info(f"Fetching Quest weather data from {start_date} to {end_date}")

#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""
    sensorlabel = ['LLNL (2m)', 'LLNL (10m)', 'LLNL (23m)', 'LLNL (52m)']
    sensorid = ['Sensor52a', 'Sensor52b', 'Sensor52c', 'Sensor52d']
    instrumentid = ['350', '351', '353', '352']
"""
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    sql = """INSERT INTO `davis_data` (`sensorid`, `sensorlabel`, `timestamp`, `temperature`) VALUES """
    values = []

    for j in range(len(instrumentid)):
        weather_data = fetch_quest_weather_data(instrumentid[j], start_date, end_date)

        if not weather_data:
            logging.error(f"No data returned for sensor {sensorid[j]}")
            continue

        dates = [datetime.strptime(entry['date'], '%Y-%m-%d %H:%M:%S') for entry in weather_data]
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
