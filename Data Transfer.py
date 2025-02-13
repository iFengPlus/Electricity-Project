from flask import Flask, request, jsonify
import dash
from dash import html, dcc
import pandas as pd

app = Flask(__name__)

# 存储数据的列表
data_store = []

@app.route('/submit', methods=['POST'])
def submit_reading():
    data = request.json
    if not all(key in data for key in ["meter_id", "timestamp", "reading_kwh"]):
        return jsonify({"error": "Missing required fields"}), 400
    
    data_store.append(data)
    return jsonify({"message": "Data received successfully"}), 200

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(data_store)

# Dash 应用
app_dash = dash.Dash(__name__, server=app, routes_pathname_prefix='/dash/')

app_dash.layout = html.Div([
    html.H1("Meter Readings"),
    dcc.Interval(id='interval-component', interval=2000, n_intervals=0),
    html.Div(id='data-display')
])

@app_dash.callback(
    dash.Output('data-display', 'children'),
    [dash.Input('interval-component', 'n_intervals')]
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
    app.run(debug=True)
