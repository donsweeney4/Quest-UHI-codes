import os
import mysql.connector
from mysql.connector import Error
import math
import logging

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,  # Set the default logging level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Format of the log messages
    handlers=[
        logging.FileHandler("debug.log"),  # Log to a file
        logging.StreamHandler()  # Also log to the console
    ]
)

def calculate_wet_bulb_temperature(temperature, humidity):
    """
    Calculate the wet bulb temperature using the Stull formula.

    :param temperature: Dry bulb temperature in Celsius
    :param humidity: Relative humidity in percentage
    :return: Wet bulb temperature in Celsius
    """
    # Using Stull's formula to calculate wet bulb temperature
    wet_bulb_temp = (
        temperature
        * math.atan(0.151977 * ((humidity + 8.313659) ** 0.5))
        + math.atan(temperature + humidity)
        - math.atan(humidity - 1.676331)
        + 0.00391838 * (humidity ** 1.5) * math.atan(0.023101 * humidity)
        - 4.686035
    )
    return wet_bulb_temp


def main():
    try:
        # Establish the connection to the MySQL database
        connection = mysql.connector.connect(
            host=os.environ['DB_HOST'],
            database='uhi',
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )

        if connection.is_connected():
            print("Connected to the database")

            cursor = connection.cursor()

            # Check if the Wet bulb temperature column exists, if not, add it
            cursor.execute("SHOW COLUMNS FROM sensor_data LIKE 'wetbulbtemperature'")
            result = cursor.fetchone()

            if not result:
                # Add the 'Wet bulb temperature' column if it does not exist
                cursor.execute("ALTER TABLE sensor_data ADD COLUMN `wetbulbtemperature` FLOAT")

            # Select rows where the recorded_at date is newer than July 4, 2024
            cursor.execute("""
                SELECT sensorid, timestamp, temperature, humidity 
                FROM sensor_data
                WHERE `timestamp` > '2024-07-01 00:00:00' AND wetbulbtemperature IS NULL
            """)
            rows = cursor.fetchall()

            # Iterate through each row and calculate the wet bulb temperature
            for row in rows:
                sensorid = row[0]
                timestamp = row[1]
                temperature = row[2]
                humidity = row[3]

                wetbulbtemperature = calculate_wet_bulb_temperature(temperature, humidity)

                # Define the SQL query
                query = """
                    UPDATE sensor_data
                    SET wetbulbtemperature = %s
                    WHERE sensorid = %s AND timestamp = %s
                """

                # Log the query and parameters for debugging purposes
                logging.debug(f"Executing query: {query} with parameters: {wetbulbtemperature}, {sensorid}, {timestamp}")

                # Execute the query with the cursor, passing the parameters as a tuple
                cursor.execute(query, (wetbulbtemperature, sensorid, timestamp))

            # Commit the transaction
            connection.commit()
            print(f"Processed {len(rows)} rows.")

    except Error as e:
        print("Error while connecting to MySQL:", e)

    finally:
        # Close the database connection
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

if __name__ == '__main__':
    logging.debug("\nStarting example_function\n ")
    main()
	
