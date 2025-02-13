import dash
from dash import dcc, html, Input, Output, State
import json
import os
import threading
from datetime import datetime

app = dash.Dash(__name__)
lock = threading.Lock()

DATA_FILE = "updated_predataset.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        return json.loads(content) if content else []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

app.layout = html.Div([
    html.H2("User Registration"),
    html.Div([
        html.Label("Meter ID:"),
        dcc.Input(id='meter-id', type='text', placeholder='e.g. 111-111-111'),
    ], style={'margin': '8px 0'}),

    html.Div([
        html.Label("User ID:"),
        dcc.Input(id='user-id', type='text', placeholder='e.g. 001001'),
    ], style={'margin': '8px 0'}),

    html.Button("Register", id='bind-btn', n_clicks=0),
    html.Div(id='bind-result', style={'color': 'blue', 'margin': '8px 0'})
])

@app.callback(
    Output('bind-result', 'children'),
    Input('bind-btn', 'n_clicks'),
    State('meter-id', 'value'),
    State('user-id', 'value')
)
def bind_meter(n_clicks, meter_id, user_id):
    if n_clicks == 0:
        return ""

    if not meter_id or not user_id:
        return "Error: meterID and userID are required."

    with lock:
        data = load_data()

        for record in data:
            if record["meterID"] == meter_id:
                if record["userID"] == "NA":
                    for rec in data:
                        if rec["userID"] == user_id and rec["meterID"] != meter_id:
                            return "Error: userID already exists, choose another."

                    record["userID"] = user_id
                    record["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    save_data(data)
                    return "Binding Successful!"
                else:
                    for rec in data:
                        if rec["userID"] == user_id and rec["meterID"] != meter_id:
                            return "Error: userID already exists, choose another."

                    record["userID"] = user_id
                    record["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    save_data(data)
                    return "Update Successful!"


        return "Error: meterID not found."

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5001, debug=True)
