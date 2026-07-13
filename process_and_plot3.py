"""
File: process_and_plot3.py

Operation:  Interactive Dash app for a single mobile-sensor track loaded from
            /home/uhi/inputData.csv (expects gps_Lat, gps_Long, gps_Alt in
            raw GPS units, plus rtcTime and degC temperature columns).

            Renders two linked, side-by-side views:
              - A Folium map (left) plotting each GPS fix as a marker.
              - A Plotly line chart (right) of temperature (degC) vs. time
                (rtcTime).

            Clicking a point on the temperature line highlights the
            corresponding GPS marker on the map (enlarged, colored red).

Usage:      Run directly to launch the Dash dev server:
                python3 process_and_plot3.py
"""
import pandas as pd
import folium
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import sys  # Added import for sys

# Function to create a Folium map
def create_map(df, zoom_start):
    center_lat, center_lon = 37.6819, -121.7680
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start)  # Use the passed zoom level
    for idx, row in df.iterrows():
        latitude, longitude, altitude = validate_and_convert(row)
        if latitude is not None and longitude is not None:
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=2,
                color='blue',
                fill=True,
                fill_color='red',
                popup=f"Index: {idx}"
            ).add_to(m)
    return m._repr_html_()

def validate_and_convert(row):
    try:
        latitude = float(row['gps_Lat']) * 1e-7
        longitude = float(row['gps_Long']) * 1e-7
        altitude = float(row['gps_Alt']) * 1e-3
        return latitude, longitude, altitude
    except ValueError as e:
        print(f"Error processing row {row}: {e}", file=sys.stderr)
        return None, None, None

# Load data
input_file = '/home/uhi/inputData.csv'
df = pd.read_csv(input_file)

# Create the initial plot
fig = px.line(df, x='rtcTime', y='degC', title='Temperature Over Time')

# Create a Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.Iframe(id='map', srcDoc=create_map(df, 12), width='100%', height='500')  # Set initial zoom level to 12
    ], style={'width': '50%', 'display': 'inline-block'}),
    html.Div([
        dcc.Graph(id='line-plot', figure=fig)
    ], style={'width': '50%', 'display': 'inline-block'}),
    dcc.Store(id='clicked-point', data=None),
    dcc.Store(id='zoom-level', data=13)  # Initialize the zoom level to 13
])

@app.callback(
    Output('clicked-point', 'data'),
    Input('line-plot', 'clickData')
)
def store_click_data(clickData):
    if clickData:
        return clickData['points'][0]['pointIndex']
    return None

@app.callback(
    Output('zoom-level', 'data'),
    Input('map', 'srcDoc'),
    State('zoom-level', 'data')
)
def store_zoom_level(_, current_zoom):
    return current_zoom  # This is a placeholder, ideally you would capture the current zoom level dynamically

@app.callback(
    Output('map', 'srcDoc'),
    [Input('clicked-point', 'data'),
     State('zoom-level', 'data')]
)
def update_map(index, zoom_level):
    center_lat, center_lon = 37.6819, -121.7680
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level)  # Use the stored zoom level
    for idx, row in df.iterrows():
        latitude, longitude, altitude = validate_and_convert(row)
        if latitude is not None and longitude is not None:
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=10 if idx == index else 2,  # Increase radius to 10 for the selected point
                color='red' if idx == index else 'blue',
                fill=True,
                fill_color='red' if idx == index else 'blue',
                popup=f"Index: {idx}"
            ).add_to(m)
    return m._repr_html_()

@app.callback(
    Output('line-plot', 'figure'),
    Input('clicked-point', 'data')
)
def update_plot(index):
    fig = px.line(df, x='rtcTime', y='degC', title='Temperature Over Time')
    if index is not None:
        fig.add_scatter(x=[df['rtcTime'][index]], y=[df['degC'][index]], mode='markers', marker=dict(color='red', size=10))
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
