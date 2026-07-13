from quart import Quart, render_template_string
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from scipy.interpolate import UnivariateSpline
import plotly.io as pio

app = Quart(__name__)

@app.route('/')
async def index():
    # Example data
    times = pd.date_range('2024-08-26', periods=100, freq='15min')
    
    # Generate synthetic temperature data and scale it between 55 and 95 degrees
    temperature = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    temperature = 20 * (temperature - np.min(temperature)) / (np.max(temperature) - np.min(temperature)) + 55  # Scale to range [55, 95]
    
    df = pd.DataFrame({'temperature': temperature}, index=times)

    # Convert time index to numerical values (seconds since epoch)
    time_seconds = df.index.astype('int64') // 10**9

    # Fit a spline with a smoothing factor
    smoothing_factor = 100.0  # Adjust based on your needs
    spline = UnivariateSpline(time_seconds, df['temperature'], s=smoothing_factor)

    # Calculate the slope (derivative) of the spline
    derivative = spline.derivative()(time_seconds)
    
    # Convert the derivative to the rate of change per minute
    df['slope'] = derivative * 60  # Multiply by 60 to get rate of change per minute

    # Create Plotly figures
    trace1 = go.Scatter(x=df.index, y=df['temperature'], mode='lines', name='Temperature Data')
    trace2 = go.Scatter(x=df.index, y=spline(time_seconds), mode='lines', name='Smoothed Spline')
    trace3 = go.Scatter(x=df.index, y=df['slope'], mode='lines', name='Derivative of Spline', yaxis='y2')

    # Create the figure with two y-axes
    fig = go.Figure()
    
    # Add the original temperature data and the smoothed spline
    fig.add_trace(trace1)
    fig.add_trace(trace2)
    
    # Add the derivative to the second y-axis
    fig.add_trace(trace3)
    
    # Update layout with specific x-axis range and titles
    fig.update_layout(
        title='Temperature Data, Smoothed Spline, and Derivative',
        xaxis_title='Time',
        yaxis=dict(title='Temperature (°F)'),
        yaxis2=dict(
            title='Slope (°F/min)', 
            overlaying='y', 
            side='right',
            titlefont=dict(color='black'),  # Ensure the title font is visible
            tickfont=dict(color='black'),  # Ensure the tick labels are visible
            position=1  # Position it correctly to the right
        ),
        xaxis=dict(range=['2024-08-26', '2024-08-27']),
        legend=dict(x=0, y=1.2, orientation='h')
    )

    # Convert Plotly figure to JSON for rendering in HTML
    graphJSON = pio.to_json(fig)

    # Render the template with the plot
    template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Temperature Plot and Derivative</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <h1>Temperature Data, Smoothed Spline, and Derivative</h1>
        <div id="plotly-div"></div>
        <script>
            var plotData = {{ plot | safe }};
            Plotly.newPlot('plotly-div', plotData.data, plotData.layout);
        </script>
    </body>
    </html>
    '''

    return await render_template_string(template, plot=graphJSON)

if __name__ == '__main__':
    app.run()
