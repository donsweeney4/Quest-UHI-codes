import pandas as pd
import os
import zipfile
import logging

# Configure logging for flexibility and control
logging.basicConfig(
    filename='/home/uhi/logs/UnZipToCSV_2.log',
    level=logging.INFO,  # Adjust logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional timestamp format
)


def convert_columns_to_float(df, header):
    """
    Convert specified columns in the dataframe to float.
    
    :param df: pandas DataFrame
    :param header: header row to be reinserted
    :return: pandas DataFrame with converted columns and header reinserted
    """
    # Convert columns to float, except the 'Timestamp' column
    for column in df.columns[1:]:
        df[column] = df[column].apply(lambda x: float(x) if isinstance(x, str) else x)
    
    # Insert the header back into the DataFrame
    df.loc[-1] = header  # Adding a row
    df.index = df.index + 1  # Shifting index
    df = df.sort_index()  # Sorting by index
    return df

def process_file(file_path):
    """
    Read a CSV file, convert necessary columns to float, and return the dataframe.
    
    :param file_path: path to the CSV file
    :return: pandas DataFrame
    """
    # Read the file with the first row as header
    df = pd.read_csv(file_path, header=0)
    
    # Get the header row to reinsert later
    header = list(df.columns)
    
    # Convert columns to float
    df = convert_columns_to_float(df, header)
    
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
    
    if csv_file_path:
        processed_df = process_file(csv_file_path)
        
        # Extract base filename and strip everything after the first hyphen, blanks, and single quotes
        base_filename = os.path.splitext(os.path.basename(csv_file_path))[0].split('-')[0].replace(' ', '').strip("'")
        
        # Save the processed dataframe back to CSV with the cleaned filename
        output_file_path = os.path.join(output_dir, f"{base_filename}.csv")
        processed_df.to_csv(output_file_path, index=False, header=False)
        
        # Cleanup the extracted CSV file
        os.remove(csv_file_path)

        # Delete the zip file after processing
        os.remove(zip_file_path) 
        
        return output_file_path
    else:
        raise FileNotFoundError("No CSV file found in the zip archive.")

def process_all_zip_files(input_directory, output_directory):
    """
    Process all zip files in a directory.
    
    :param input_directory: path to the directory containing zip files
    :param output_directory: directory to save the processed files
    :return: list of paths to processed CSV files
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    processed_files = []
    
    for filename in os.listdir(input_directory):
        if filename.endswith(".zip"):
            zip_file_path = os.path.join(input_directory, filename)
            processed_file_path = process_zip_file(zip_file_path, input_directory, output_directory)
            processed_files.append(processed_file_path)
    
    return processed_files

# Example usage
input_directory = 'email_attachments'
output_directory = 'SensorData'

# Process all zip files in the input directory and save to the output directory
processed_files = process_all_zip_files(input_directory, output_directory)

# Output the paths to the processed files
print("Processed files:", processed_files)
logging.info("Processed files: %s", processed_files)