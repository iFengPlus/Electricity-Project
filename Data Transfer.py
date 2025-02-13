import dash
from dash import html, dcc
import pandas as pd
from dash.dependencies import Input, Output

# 存储数据的列表
data_store = []

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Meter Readings"),
    dcc.Input(id='meter_id', type='text', placeholder='Enter Meter ID'),
    dcc.Input(id='timestamp', type='text', placeholder='Enter Timestamp'),
    dcc.Input(id='reading_kwh', type='number', placeholder='Enter kWh Reading'),
    html.Button('Submit', id='submit-btn', n_clicks=0),
    html.Div(id='message'),
    dcc.Interval(id='interval-component', interval=2000, n_intervals=0),
    html.Div(id='data-display')
])

@app.callback(
    Output('message', 'children'),
    Input('submit-btn', 'n_clicks'),
    [dash.State('meter_id', 'value'),
     dash.State('timestamp', 'value'),
     dash.State('reading_kwh', 'value')]
)
def submit_reading(n_clicks, meter_id, timestamp, reading_kwh):
    if n_clicks > 0 and meter_id and timestamp and reading_kwh is not None:
        data_store.append({"meter_id": meter_id, "timestamp": timestamp, "reading_kwh": reading_kwh})
        return "Data received successfully"
    return ""

@app.callback(
    Output('data-display', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_data(n):
    df = pd.DataFrame(data_store)
    if df.empty:
        return "No data available"
    return html.Table([
        html.Tr([html.Th(col) for col in df.columns])
    ] + [
        html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))
    ])

if __name__ == '__main__':
    app.run_server(debug=True)