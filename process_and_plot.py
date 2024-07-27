import pandas as pd
import folium
import argparse
import sys

def validate_and_convert(row):
    try:
        # Validate and convert latitude, longitude, and altitude
        latitude = float(row['gps_Lat']) * 1e-7
        longitude = float(row['gps_Long']) * 1e-7
        altitude = float(row['gps_Alt']) * 1e-3
        return latitude, longitude, altitude
    except ValueError as e:
        print(f"Error processing row {row}: {e}", file=sys.stderr)
        return None, None, None

def main(input_file):
    # Read the CSV file
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"File {input_file} not found", file=sys.stderr)
        sys.exit(1)

    # Print the columns of the DataFrame to debug the column names
    print("Columns in the CSV file:", df.columns)

    # Check for necessary columns
#    required_columns = ['timestamp', 'latitude', 'longitude', 'altitude']
#    if not all(column in df.columns for column in required_columns):
#        print(f"Input file must contain the following columns: {required_columns}", file=sys.stderr)
#        sys.exit(1)

    # Center of Livermore, California
    center_lat, center_lon = 37.6819, -121.7680

    # Create a map centered around Livermore, California with initial zoom level of 18
    m = folium.Map(location=[center_lat, center_lon], zoom_start=18)

    # Overlay the coordinate pairs on the map as small colored dots
    for idx, row in df.iterrows():
        latitude, longitude, altitude = validate_and_convert(row)
        if latitude is not None and longitude is not None:
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=2,
                color='blue',
                fill=True,
                fill_color='red'
            ).add_to(m)

    # Save the map as an HTML file
    m.save('map_with_coordinates.html')
    print("Map has been created and saved as map_with_coordinates.html")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process a CSV file and plot points on a map.')
    parser.add_argument('--input', required=True, help='Input CSV file name')
    args = parser.parse_args()

    main(args.input)
