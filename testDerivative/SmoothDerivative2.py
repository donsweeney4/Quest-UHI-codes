from quart import Quart, render_template_string
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from scipy.interpolate import UnivariateSpline
import plotly.io as pio
from plotly.subplots import make_subplots

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

    # Use a smoothing factor of 100
    smoothing_factor = 100
    spline = UnivariateSpline(time_seconds, df['temperature'], s=smoothing_factor)

    # Calculate the slope (derivative) of the spline
    derivative = spline.derivative()(time_seconds)
    
    # Convert the derivative to the rate of change per minute
    df['slope'] = derivative * 60  # Multiply by 60 to get rate of change per minute

    # Create Plotly subplots: one for the temperature/spline and one for the derivative
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15,
                        subplot_titles=("Temperature Data and Smoothed Spline", "Derivative of Smoothed Spline"))

    # Plot temperature data and smoothed spline on the first subplot
    trace1 = go.Scatter(x=df.index, y=df['temperature'], mode='lines', name='Temperature Data')
    trace2 = go.Scatter(x=df.index, y=spline(time_seconds), mode='lines', name='Smoothed Spline')

    fig.add_trace(trace1, row=1, col=1)
    fig.add_trace(trace2, row=1, col=1)

    # Plot the derivative on the second subplot
    trace3 = go.Scatter(x=df.index, y=df['slope'], mode='lines', name='Derivative of Spline')

    fig.add_trace(trace3, row=2, col=1)

    # Update layout for the entire figure
    fig.update_layout(
        height=800,  # Increase height for better spacing
        title_text="Temperature Analysis",
        xaxis=dict(range=['2024-08-26', '2024-08-27']),
        xaxis2=dict(range=['2024-08-26', '2024-08-27']),  # Sync x-axis range for the second plot
        yaxis_title="Temperature (°F)",
        yaxis2_title="Slope (°F/min)"
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
        <h1>Temperature Analysis</h1>
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
