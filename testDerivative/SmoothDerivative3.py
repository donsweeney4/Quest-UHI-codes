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
    
    # Generate synthetic temperature data
    temperature = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    
    # Scale temperature data to two different ranges
    temperature1 = 40 * (temperature - np.min(temperature)) / (np.max(temperature) - np.min(temperature)) + 55  # Scale to range [55, 95]
    temperature2 = 50 * (temperature - np.min(temperature)) / (np.max(temperature) - np.min(temperature)) + 50  # Scale to range [50, 100]
    
    df = pd.DataFrame({
        'temperature1': temperature1,
        'temperature2': temperature2
    }, index=times)

    # Convert time index to numerical values (seconds since epoch)
    time_seconds = df.index.astype('int64') // 10**9

    # Use a smoothing factor of 100 for both temperature traces
    smoothing_factor = 500
    spline1 = UnivariateSpline(time_seconds, df['temperature1'], s=smoothing_factor)
    
    smoothing_factor = 500
    spline2 = UnivariateSpline(time_seconds, df['temperature2'], s=smoothing_factor)

    # Calculate the slope (derivative) of the splines
    derivative1 = spline1.derivative()(time_seconds) * 60  # Convert to rate of change per minute
    
    derivative2 = spline2.derivative()(time_seconds) * 60  # Convert to rate of change per minute

    df['slope1'] = derivative1
    df['slope2'] = derivative2

    # Create Plotly subplots: one for the temperature/spline and one for the derivatives
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15,
                        subplot_titles=("Temperature Data and Smoothed Splines", "Derivatives of Smoothed Splines"))

    # Plot temperature data and smoothed splines on the first subplot
    trace1 = go.Scatter(x=df.index, y=df['temperature1'], mode='lines', name='Temperature Data [55, 95]')
    trace2 = go.Scatter(x=df.index, y=spline1(time_seconds), mode='lines', name='Smoothed Spline [55, 95]')
    
    trace3 = go.Scatter(x=df.index, y=df['temperature2'], mode='lines', name='Temperature Data [50, 100]')
    trace4 = go.Scatter(x=df.index, y=spline2(time_seconds), mode='lines', name='Smoothed Spline [50, 100]')

    fig.add_trace(trace1, row=1, col=1)
    fig.add_trace(trace2, row=1, col=1)
    fig.add_trace(trace3, row=1, col=1)
    fig.add_trace(trace4, row=1, col=1)

    # Plot the derivatives on the second subplot
    trace5 = go.Scatter(x=df.index, y=df['slope1'], mode='lines', name='Derivative of Spline [55, 95]')
    trace6 = go.Scatter(x=df.index, y=df['slope2'], mode='lines', name='Derivative of Spline [50, 100]')

    fig.add_trace(trace5, row=2, col=1)
    fig.add_trace(trace6, row=2, col=1)

    # Update layout for the entire figure
    fig.update_layout(
        height=800,  # Increase height for better spacing
        title_text="Temperature Analysis with Two Different Ranges",
        xaxis=dict(range=['2024-08-26', '2024-08-27']),
        yaxis_title="Temperature (°F)",
        yaxis2_title="Slope (°F/min)",
        legend=dict(x=0.5, y=-0.2, orientation='h', xanchor='center', yanchor='top'),
        template="plotly_white"  # Use a white background for better visibility
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
        <h1>Temperature Analysis with Two Different Ranges</h1>
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
