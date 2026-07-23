"""
File: ProcessSensorPushData.py

Operation:  Combines the three-stage SensorPush ingest pipeline into a single script,
            run in order:

            1. Scan incoming mail in /home/uhi/Maildir, extract .zip attachments
               (renamed with a UUID prefix for uniqueness), move them to
               /home/uhi/email_attachments, and delete the processed mail so it
               isn't picked up again.

            2. Unzip each file in /home/uhi/email_attachments, clean the contained
               CSV (convert columns to float, fix accidental Fahrenheit exports,
               trim accidental 1-minute exports to 15-minute intervals), and save
               the cleaned CSV to /home/uhi/SensorData (filename = sensor ID).
               Zip files that fail to process are moved to
               /home/uhi/failed_attachments instead of being retried forever.

            3. Read each CSV in /home/uhi/SensorData, insert its rows into the
               MySQL sensor_data table (ON DUPLICATE KEY UPDATE, keyed on
               sensorid + timestamp), then move the processed CSV to
               /home/uhi/archived_data with a Unix timestamp suffix.

Frequency:  The program runs every 5 minutes with cron.
"""
import os
import email
import mailbox
from email.policy import default
import uuid
import csv
import shutil
import time
import pandas as pd
import zipfile
import mysql.connector
from mysql.connector import Error
import logging

# Configure logging for flexibility and control
log_file = '/home/uhi/ProcessSensorPushData.log'

# Blank line between runs makes the log file easier to read
with open(log_file, 'a') as f:
    f.write('\n')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,  # Adjust logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional timestamp format
)

# Directories used across the pipeline
maildir_path = "/home/uhi/Maildir"
email_attachments_dir = "/home/uhi/email_attachments"
sensor_data_dir = "/home/uhi/SensorData"
failed_attachments_dir = "/home/uhi/failed_attachments"
archive_dir = "/home/uhi/archived_data"


# ---------------------------------------------------------------------------
# Stage 1: Maildir -> email_attachments
# ---------------------------------------------------------------------------

def process_attachment(part, email_number):
    filename = part.get_filename()
    if filename:
        # Generate a unique filename using UUID
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(email_attachments_dir, unique_filename)
        with open(filepath, 'wb') as f:
            f.write(part.get_payload(decode=True))
        print(f"Moved attachment to email_attachments: {unique_filename}")
        logging.info(f"Moved attachment to email_attachments: {unique_filename}")
        return True
    return False


def process_incoming_mail_attachments():
    """
    Process all mail in the Maildir.

    :return: number of attachments extracted
    """
    os.makedirs(email_attachments_dir, exist_ok=True)

    maildir = mailbox.Maildir(maildir_path, factory=None, create=False)

    attachment_count = 0

    for i, key in enumerate(maildir.keys(), start=1):
        msg = maildir[key]
        print('Processing new email in maildir: ' + key)
        logging.info('Processing new email in maildir: ' + key)
        email_msg = email.message_from_bytes(msg.as_bytes(), policy=default)
        for part in email_msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is not None:
                if process_attachment(part, i):
                    attachment_count += 1
        print('Removing email in maildir: ' + key)
        logging.info('Removing email in maildir: ' + key)
        maildir.discard(key)  # Remove the email after processing

    return attachment_count


# ---------------------------------------------------------------------------
# Stage 2: email_attachments -> SensorData
# ---------------------------------------------------------------------------

def convert_columns_to_float(df):
    """
    Convert all columns except the first (Timestamp) to float.

    :param df: pandas DataFrame
    :return: pandas DataFrame with converted columns
    """
    for column in df.columns[1:]:
        df[column] = df[column].apply(lambda x: float(x) if isinstance(x, str) else x)
    return df


def fix_temperature_units(df, temp_col_index=1):
    """
    SensorPush exports are expected in Celsius. Users sometimes accidentally
    export in Fahrenheit instead. A temperature above 50 is implausible for
    Celsius (122F) but common for an accidental Fahrenheit export, so treat
    it as a signal that the whole column is in Fahrenheit and convert it.

    :param df: pandas DataFrame (numeric columns already converted to float)
    :param temp_col_index: column index of the temperature column
    :return: pandas DataFrame with temperature corrected to Celsius
    """
    temp_col = df.columns[temp_col_index]
    if df[temp_col].max() > 50:
        df[temp_col] = (df[temp_col] - 32) * 5 / 9
    return df


def trim_to_15_minute_intervals(df, timestamp_col_index=0):
    """
    SensorPush exports are expected on 15-minute intervals. Users sometimes
    accidentally export at 1-minute resolution instead. If the typical gap
    between readings is well under 15 minutes, keep only the rows that fall
    on a 15-minute boundary (:00, :15, :30, :45) and drop the rest.

    :param df: pandas DataFrame (Timestamp column still a parseable string)
    :param timestamp_col_index: column index of the timestamp column
    :return: pandas DataFrame trimmed to 15-minute intervals
    """
    timestamp_col = df.columns[timestamp_col_index]
    timestamps = pd.to_datetime(df[timestamp_col])

    if len(timestamps) < 2:
        return df

    typical_gap = timestamps.diff().dropna().median()
    if typical_gap <= pd.Timedelta(minutes=5):
        mask = (timestamps.dt.minute % 15 == 0) & (timestamps.dt.second == 0)
        df = df[mask].reset_index(drop=True)

    return df


def process_file(file_path):
    """
    Read a CSV file, convert necessary columns to float, correct accidental
    Fahrenheit/1-minute-interval imports, and return the dataframe.

    :param file_path: path to the CSV file
    :return: pandas DataFrame
    """
    # Read the file with the first row as header
    df = pd.read_csv(file_path, header=0)

    # Get the header row to reinsert later
    header = list(df.columns)

    # Convert columns to float
    df = convert_columns_to_float(df)

    # Correct accidental Fahrenheit / 1-minute-interval imports
    df = fix_temperature_units(df)
    df = trim_to_15_minute_intervals(df)

    # Insert the header back into the DataFrame
    df.loc[-1] = header  # Adding a row
    df.index = df.index + 1  # Shifting index
    df = df.sort_index()  # Sorting by index

    return df


def process_zip_file(zip_file_path, extract_to, output_dir):
    """
    Unzip a zip file, process the contained CSV file, and save the processed file.

    :param zip_file_path: path to the zip file
    :param extract_to: directory to extract the files to
    :param output_dir: directory to save the processed files
    :return: path to the processed CSV file
    """
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    # Find the extracted CSV file
    extracted_files = os.listdir(extract_to)
    csv_file_path = None
    for file in extracted_files:
        if file.endswith(".csv"):
            csv_file_path = os.path.join(extract_to, file)
            break

    try:
        if csv_file_path:
            processed_df = process_file(csv_file_path)

            # Extract base filename and strip everything after the first hyphen, blanks, and single quotes
            base_filename = os.path.splitext(os.path.basename(csv_file_path))[0].split('-')[0].replace(' ', '').strip("'")
            logging.info(f"Cleaned CSV filename: {base_filename}.csv")

            # Save the processed dataframe back to CSV with the cleaned filename
            output_file_path = os.path.join(output_dir, f"{base_filename}.csv")
            processed_df.to_csv(output_file_path, index=False, header=False)

            # Delete the zip file after processing
            os.remove(zip_file_path)

            return output_file_path
        else:
            raise FileNotFoundError("No CSV file found in the zip archive.")
    finally:
        # Always clean up the extracted CSV, whether processing succeeded or failed
        if csv_file_path and os.path.exists(csv_file_path):
            os.remove(csv_file_path)


def process_all_zip_files(input_directory, output_directory, quarantine_directory):
    """
    Process all zip files in a directory. A zip file that fails to process is
    moved to quarantine_directory instead of being left in place, so it isn't
    retried forever and doesn't block the other zip files in the batch.

    :param input_directory: path to the directory containing zip files
    :param output_directory: directory to save the processed files
    :param quarantine_directory: directory to move zip files that fail to process
    :return: list of paths to processed CSV files
    """
    # Ensure the output/quarantine directories exist
    os.makedirs(output_directory, exist_ok=True)
    os.makedirs(quarantine_directory, exist_ok=True)

    processed_files = []

    for filename in os.listdir(input_directory):
        if filename.endswith(".zip"):
            zip_file_path = os.path.join(input_directory, filename)
            try:
                processed_file_path = process_zip_file(zip_file_path, input_directory, output_directory)
                processed_files.append(processed_file_path)
            except Exception as e:
                print(f"Failed to process {filename}, moving to quarantine: {e}")
                logging.error(f"Failed to process {filename}, moving to quarantine: {e}")
                if os.path.exists(zip_file_path):
                    shutil.move(zip_file_path, os.path.join(quarantine_directory, filename))

    return processed_files


def unzip_to_csv():
    processed_files = process_all_zip_files(email_attachments_dir, sensor_data_dir, failed_attachments_dir)
    print("Unzipped, cleaned, and saved to SensorData:", processed_files)
    logging.info("Unzipped, cleaned, and saved to SensorData: %s", processed_files)


# ---------------------------------------------------------------------------
# Stage 3: SensorData -> MySQL
# ---------------------------------------------------------------------------

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


def insert_data(cursor, sensorid, timestamp, temperature, humidity):
    insert_query = """INSERT INTO sensor_data (sensorid, timestamp, temperature, humidity)
                      VALUES (%s, %s, %s, %s)
                      ON DUPLICATE KEY UPDATE
                      temperature = VALUES(temperature),
                      humidity = VALUES(humidity)"""
    record = (sensorid, timestamp, temperature, humidity)
    cursor.execute(insert_query, record)


def process_csv_files(connection):
    cursor = connection.cursor()
    for filename in os.listdir(sensor_data_dir):
        if filename.endswith(".csv"):
            file_path = os.path.join(sensor_data_dir, filename)

            # Use the full base filename as sensorid
            base_filename = os.path.splitext(filename)[0]
            sensorid = base_filename

            # sensorid column is varchar(20); truncate anything longer so the insert doesn't fail
            if len(sensorid) > 20:
                print(f"sensorid '{sensorid}' is longer than 20 characters, truncating to '{sensorid[:20]}'")
                logging.info(f"sensorid '{sensorid}' is longer than 20 characters, truncating to '{sensorid[:20]}'")
                sensorid = sensorid[:20]

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


def csv_to_sql():
    connection = connect_to_database()
    if connection is not None and connection.is_connected():
        process_csv_files(connection)
        connection.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def has_pending_work():
    """
    True if there is a zip file waiting to be unzipped in email_attachments/
    or a CSV waiting to be inserted in SensorData/. A prior run can leave
    work behind here (e.g. it crashed after unzipping but before the DB
    insert), so this must be checked even when no new mail came in this run.
    """
    pending_zips = os.path.isdir(email_attachments_dir) and any(
        f.endswith(".zip") for f in os.listdir(email_attachments_dir)
    )
    pending_csvs = os.path.isdir(sensor_data_dir) and any(
        f.endswith(".csv") for f in os.listdir(sensor_data_dir)
    )
    return pending_zips or pending_csvs


def main():
    attachment_count = process_incoming_mail_attachments()
    logging.info(f"New attachments found this run: {attachment_count}")

    if not has_pending_work():
        print("No new incoming mail with attachments and nothing pending to process; exiting.")
        logging.info("No new incoming mail with attachments and nothing pending to process; exiting.")
        return

    unzip_to_csv()
    csv_to_sql()


if __name__ == "__main__":
    main()
