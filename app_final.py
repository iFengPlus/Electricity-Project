import dash
from dash import html, dcc, Input, Output, State, ctx
import pandas as pd
import plotly.graph_objects as go
import os
import threading
from datetime import datetime, timedelta
import json
import time
from collections import defaultdict


# ↓ Some Key Functions ↓
# change format of time in meter_data(str to datetime)
def format_meter_data():
    
    global meter_data  

    for meter_id in meter_data:
        for entry in meter_data[meter_id]:
            if isinstance(entry["timestamp"], str): 
                entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")



def read_json_files(meter_data_path, registration_path):
    #read meter_data and Registration when restart
    try:
        with open(meter_data_path, 'r', encoding='utf-8') as file:
            meter_data = json.load(file)
        
        with open(registration_path, 'r', encoding='utf-8') as file:
            registration_data = json.load(file)
        
        return meter_data, registration_data
    
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None, None


def save_user(data):
    #Save Registration data to json file 
    with open(registration_data_location, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_meter(data):
    #Save Meter data to json file, but datetime can not store, so change format 1st.
    for meter_id in data:
        for entry in data[meter_id]:
            if isinstance(entry["timestamp"], datetime):
                entry["timestamp"] = entry["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")

    with open(meter_data_location, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# server shut down(use when at 0:00)
def shutdown_server():
    time.sleep(2)
    save_user(registration_data)
    save_meter(meter_data)
    
    os._exit(0)

# Find closest timestamp when meter reading
def get_reading_at(readings, target_time):
    readings_sorted = sorted(readings, key=lambda x: abs(x["timestamp"] - target_time))
    return readings_sorted[0]["reading_kwh"] if readings_sorted else None   

# Data Insert Function
# HOYT PLS CHECK HERE
def write_to_meter_data(meter_id, timestamp, reading_kwh):
    global meter_data  # make sure we change globally

    # make sure format can use
    if isinstance(timestamp, str):
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

    # make sure have this meter in the list
    if meter_id not in meter_data:
        meter_data[meter_id] = []

    # make sure data in list are in good structure and format
    for entry in meter_data[meter_id]:
        if isinstance(entry["timestamp"], str):
            entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")

    # Check 1: Is the timestamp already exist in meter_data?
    for entry in meter_data[meter_id]:
        if entry["timestamp"] == timestamp:
            return "Error: Duplicate timestamp. Data not inserted."

    # Check 2: Find the exact insert place
    index = 0
    while index < len(meter_data[meter_id]) and meter_data[meter_id][index]["timestamp"] < timestamp:
        index += 1

    # insert it
    meter_data[meter_id].insert(index, {"timestamp": timestamp, "reading_kwh": reading_kwh})
    return "Data inserted successfully!"


# ↓ Dash App Codes ↓
# Define dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
lock = threading.Lock()



# Main Page Layout
app.layout = html.Div([
    html.H1("Smart Meter Management System", style={'textAlign': 'center'}),

    # Navigation Column, for semi-apps change
    html.Div([
        html.Button("User Registration", id="btn-user-reg", n_clicks=0, style={'margin': '5px'}),
        html.Button("User Query", id="btn-user-query", n_clicks=0, style={'margin': '5px'}),
        html.Button("Government Query", id="btn-gov-query", n_clicks=0, style={'margin': '5px'}),
        html.Button("Meter Reading", id="btn-meter-read", n_clicks=0, style={'margin': '5px'}),
        html.Button("Aggregate Meter Data", id="aggregate-btn", n_clicks=0, style={'margin': '5px'}),
        html.Button("Server Shut Down", id="btn-shutdown", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'red', 'color': 'white'}),
    ], style={'textAlign': 'center'}),

    html.Hr(),  # here I add a split line to beautify page

    html.Button("Back", id="btn-back", n_clicks=0, style={'display': 'none'}),
    # change semi-pages
    html.Div(id="page-content", style={'padding': '20px'}),
    html.Div(id="aggregate-result", style={'color': 'green', 'textAlign': 'center', 'margin': '10px'}),

    dcc.Location(id='shutdown-url', refresh=True),

    html.Div(id="shutdown-message")
    
])

# User Registration Page
def user_registration_page():
    return html.Div([
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
        html.Div(id='bind-result', style={'color': 'blue', 'margin': '8px 0'}),

        html.Button("Back", id="btn-back", n_clicks=0, style={'margin-top': '10px'})
    ])



# User Query Page
def user_query_page():
    return html.Div([
        html.H2("Electricity Usage Query System"),
        html.Div([
            html.Label("User ID:"),
            dcc.Input(id="user-id", type="text", placeholder="Enter User ID"),
            html.Button("Login", id="login-btn", n_clicks=0),
            html.Div(id="login-status"),
        ], style={"margin-bottom": "20px"}),

        html.Div([
            html.Label("Select Time Period for Electricity Usage Query:"),
            dcc.Dropdown(
                id="query-type",
                options=[
                    {"label": "Last 30 Minutes", "value": "last_30_min"},
                    {"label": "Today", "value": "today"},
                    {"label": "Yesterday", "value": "yesterday"},
                    {"label": "Past Week", "value": "past_week"},
                    {"label": "Past Month", "value": "past_month"}
                ],
                placeholder="Select Query Type"
            ),
            html.Button("Query", id="query-btn", n_clicks=0),
            html.Div(id="user-query-result"),
            dcc.Graph(id="user-usage-graph"),
        ], id="query-section", style={"display": "none"}),

        html.Button("Back", id="btn-back", n_clicks=0, style={'margin-top': '10px'})
    ])

# Government Query Page
def government_query_page():
    return html.Div([
        html.H2("Electricity Usage Query System (Government)"),
        
        html.Label("Select Region:"),
        dcc.Dropdown(
            id="region-dropdown",
            options=[{"label": reg, "value": reg} for reg in sorted(set(u["region"] for u in registration_data))],
            placeholder="Select Region"
        ),

        html.Label("Select Area:"),
        dcc.Dropdown(id="area-dropdown", placeholder="Select Area"),

        html.Label("Select Time Period:"),
        dcc.Dropdown(
            id="query-type",
            options=[
                {"label": "Last 30 Minutes", "value": "last_30_min"},
                {"label": "Today", "value": "today"},
                {"label": "Yesterday", "value": "yesterday"},
                {"label": "Past Week", "value": "past_week"},
                {"label": "Past Month", "value": "past_month"}
            ],
            placeholder="Select Query Type"
        ),

        html.Button("Query", id="query-btn", n_clicks=0),
        html.Div(id="gov-query-result"),
        dcc.Graph(id="gov-usage-graph"),

        html.Button("Back", id="btn-back", n_clicks=0, style={'margin-top': '10px'})
    ])


def write_to_meter_data(meter_id, timestamp, reading_kwh):
    global meter_data  # make sure we change globally

    # make sure format can use
    if isinstance(timestamp, str):
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

    # make sure have this meter in the list
    if meter_id not in meter_data:
        meter_data[meter_id] = []

    # make sure data in list are in good structure and format
    for entry in meter_data[meter_id]:
        if isinstance(entry["timestamp"], str):
            entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")

    # Check 1: Is the timestamp already exist in meter_data?
    for entry in meter_data[meter_id]:
        if entry["timestamp"] == timestamp:
            return "❌ Error: Duplicate timestamp. Data not inserted."

    # Check 2: Find the exact insert place
    index = 0
    while index < len(meter_data[meter_id]) and meter_data[meter_id][index]["timestamp"] < timestamp:
        index += 1

    # insert it
    meter_data[meter_id].insert(index, {"timestamp": timestamp, "reading_kwh": reading_kwh})
    return "✅ Data inserted successfully!"

# Meter reading page
def meter_reading_page():
    return html.Div([
        html.H1("Meter Readings"),
        
        # 
        dcc.Input(id='meter_id', type='text', placeholder='Enter Meter ID'),
        dcc.Input(id='timestamp', type='text', placeholder='Enter Timestamp (YYYY-MM-DDTHH:MM:SS)'),
        dcc.Input(id='reading_kwh', type='number', placeholder='Enter kWh Reading'),
        
        # Submit button
        html.Button('Submit', id='submit-btn', n_clicks=0),
        
        # message respond
        html.Div(id='message'),

        # data refresh automatically
        dcc.Interval(id='interval-component', interval=2000, n_intervals=0),

        # display
        html.Div(id='data-display'),
    ])



# after-shoutdown page layout
def shutdown_page():
    return html.Div(
        style={"textAlign": "center", "fontSize": "24px", "marginTop": "10%"},  # location define
        children=[
            "Now is 0:00 lah! Server also need a rest🌙", html.Br(), html.Br(),
            "Good Night!\xa0\xa0\xa0\xa0晚安!\xa0\xa0\xa0\xa0Selamat Malam!\xa0\xa0\xa0\xa0இனிய இரவு!"
        ]
    )#dash cannot use /n or Enter to change lines, so after asking chatgpt, we use "\xa0"

# data cleaning on a monthly basis
def aggregate_meter_data():
    global meter_data
    
    aggregated_data = {}

    for meter_id, readings in meter_data.items():
        monthly_totals = {}

        for entry in readings:
            timestamp = entry["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

            month_key = timestamp.strftime("%Y-%m")  # e.g., "2024-02"
            
            # sum kWh
            if month_key not in monthly_totals:
                monthly_totals[month_key] = 0
            monthly_totals[month_key] += entry["reading_kwh"]

        aggregated_data[meter_id] = [
            {"timestamp": f"{month_key}-01T00:00:00", "reading_kwh": total}
            for month_key, total in monthly_totals.items()
        ]

    # cover the original data
    meter_data = aggregated_data

    # save the aggregated ones
    save_meter(meter_data)
    return "Aggregation completed! Monthly data saved."

# ↓ Callback Functions ↓
#rules for registration
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
        data = registration_data

        for record in data:
            if record["meterID"] == meter_id:
                if record["userID"] == "NA":
                    for rec in data:
                        if rec["userID"] == user_id and rec["meterID"] != meter_id:
                            return "Error: userID already exists, choose another."

                    record["userID"] = user_id
                    #record["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    save_user(data)
                    return "Binding Successful!"
                else:
                    for rec in data:
                        if rec["userID"] == user_id and rec["meterID"] != meter_id:
                            return "Error: userID already exists, choose another."

                    record["userID"] = user_id
                    #record["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    save_user(data)
                    return "Update Successful!"

        return "Error: meterID not found."

#rules for user query
@app.callback(
    [Output("login-status", "children"), 
     Output("query-section", "style"),
     Output("user-query-result", "children"), 
     Output("user-usage-graph", "figure")],
    [Input("login-btn", "n_clicks"), 
     Input("query-btn", "n_clicks")],
    [State("user-id", "value"), State("query-type", "value")]
)
def handle_user_query(login_clicks, query_clicks, user_id, query_type):
    triggered_id = ctx.triggered_id  

    if triggered_id == "login-btn":
        user = next((u for u in registration_data if u["userID"] == user_id), None)
        if user:
            return (f"Login successful! Meter ID: {user['meterID']}", {"display": "block"}, "", go.Figure())
        else:
            return ("User not found. Please enter a valid User ID.", {"display": "none"}, "", go.Figure())

    elif triggered_id == "query-btn":
        format_meter_data()
        user = next((u for u in registration_data if u["userID"] == user_id), None)

        if not user:
            return ("User not found.", {"display": "none"}, "No user data available.", go.Figure())

        meter_id = user["meterID"]
        if meter_id not in meter_data:
            return ("No electricity data found.", {"display": "block"}, "No data for this meter.", go.Figure())

        readings = meter_data[meter_id]
        if len(readings) < 2:
            return ("No Sufficient Data Available", {"display": "block"}, "Not enough data to calculate consumption.", go.Figure())

        latest_timestamp = max(r["timestamp"] for r in readings) 
        now = latest_timestamp

        if query_type == "last_30_min":
            start_time = now - timedelta(minutes=30)
        elif query_type == "today":
            start_time = now.replace(hour=0, minute=0, second=0)
        elif query_type == "yesterday":
            start_time = now - timedelta(days=1)
            end_time = start_time + timedelta(hours=24)
        elif query_type == "past_week":
            start_time = now - timedelta(days=7)
        elif query_type == "past_month":
            start_time = now - timedelta(days=30)

        filtered_readings = [r for r in readings if r["timestamp"] >= start_time]
        if query_type == "yesterday":
            filtered_readings = [r for r in readings if start_time <= r["timestamp"] < end_time]

        if len(filtered_readings) < 2:
            return ("No Data Available", {"display": "block"}, "Not enough data points for calculation.", go.Figure())

        timestamps = [r["timestamp"] for r in filtered_readings]
        consumption_deltas = [
            filtered_readings[i]["reading_kwh"] - filtered_readings[i - 1]["reading_kwh"]
            for i in range(1, len(filtered_readings))
        ]

        if query_type in ["past_week", "past_month"]:
            daily_usage = {}
            for i in range(1, len(timestamps)):
                day = timestamps[i - 1].strftime("%Y-%m-%d") 
                daily_usage[day] = daily_usage.get(day, 0) + consumption_deltas[i - 1]

            time_labels = list(daily_usage.keys())
            consumption_values = list(daily_usage.values())
        else:
            time_labels = [
                f"{timestamps[i - 1].strftime('%m%d %H:%M')} → {timestamps[i].strftime('%H:%M')}"
                for i in range(1, len(timestamps))
            ]
            consumption_values = consumption_deltas

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=time_labels, 
            y=consumption_values, 
            name="Electricity Consumption",
            marker_color="royalblue"
        ))

        fig.update_layout(
            title="Electricity Consumption",
            xaxis_title="Time Period",
            yaxis_title="Consumption (kWh)",
            xaxis=dict(showgrid=True, tickangle=45),
            yaxis=dict(showgrid=True),
            template="plotly_white"
        )

        return (f"⚡ Total electricity usage: {sum(consumption_values):.2f} kWh", {"display": "block"}, "", fig)

    return ("", {"display": "none"}, "", go.Figure())

#rules for government query_1
@app.callback(
    Output("area-dropdown", "options"),
    Input("region-dropdown", "value")
)
def update_area_options(selected_region):
    if selected_region:
        areas = sorted(set(u["area"] for u in registration_data if u["region"] == selected_region))
        return [{"label": area, "value": area} for area in areas]
    return []
#rules for government query_2
def get_time_window(readings, query_type):
    if not readings:
        return None, None
    latest_timestamp = max(r["timestamp"] for r in readings)
    if query_type == "last_30_min":
        start_time = latest_timestamp - timedelta(minutes=30)
        end_time = latest_timestamp
    elif query_type == "today":
        start_time = latest_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = latest_timestamp
    elif query_type == "yesterday":
        start_time = (latest_timestamp - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
    elif query_type == "past_week":
        start_time = latest_timestamp - timedelta(days=7)
        end_time = latest_timestamp
    elif query_type == "past_month":
        start_time = latest_timestamp - timedelta(days=30)
        end_time = latest_timestamp
    else:
        start_time, end_time = None, None
    return start_time, end_time

def floor_to_half_hour(dt):
    minute = (dt.minute // 30) * 30
    return dt.replace(minute=minute, second=0, microsecond=0)
@app.callback(
    [Output("gov-query-result", "children"), Output("gov-usage-graph", "figure")],
    Input("query-btn", "n_clicks"),
    [State("region-dropdown", "value"), State("area-dropdown", "value"), State("query-type", "value")]
)
def query_data(n_clicks, region, area, query_type):
    if not (region and area and query_type):
        return "Please select region, area, and time period.", go.Figure()

    meters = [u["meterID"] for u in registration_data if u["region"] == region and u["area"] == area]
    if not meters:
        return "No registration data found for the selected region and area.", go.Figure()

    meter_data_usage = {}
    overall_start = None
    overall_end = None
    for meter_id in meters:
        if meter_id not in meter_data:
            continue
        readings = meter_data[meter_id]
        start_time, end_time = get_time_window(readings, query_type)
        if start_time is None:
            continue
        filtered = [r for r in readings if start_time <= r["timestamp"] <= end_time]
        if not filtered:
            continue
        filtered.sort(key=lambda r: r["timestamp"])
        meter_data_usage[meter_id] = filtered
        if overall_start is None or start_time < overall_start:
            overall_start = start_time
        if overall_end is None or end_time > overall_end:
            overall_end = end_time

    if not meter_data_usage:
        return " No electricity data found for the selected criteria.", go.Figure()

    # Determine the resolution/bucketing based on query_type
    if query_type in ["today", "yesterday"]:
        resolution = timedelta(hours=1)
        fmt = "%Y-%m-%d %H:%M"
        bucket_start = overall_start.replace(minute=0, second=0, microsecond=0)
    elif query_type in ["past_week", "past_month"]:
        resolution = timedelta(days=1)
        fmt = "%Y-%m-%d"
        bucket_start = overall_start.date()
    elif query_type == "last_30_min":
        resolution = timedelta(minutes=1)
        fmt = "%Y-%m-%d %H:%M"
        bucket_start = overall_start.replace(second=0, microsecond=0)
    else:
        resolution = timedelta(hours=1)
        fmt = "%Y-%m-%d %H:%M"
        bucket_start = overall_start.replace(minute=0, second=0, microsecond=0)

    # Create buckets
    buckets = []
    if query_type in ["past_week", "past_month"]:
        current = bucket_start
        end_date = overall_end.date()
        while current <= end_date:
            buckets.append(current)
            current += timedelta(days=1)
    else:
        current = bucket_start
        while current <= overall_end:
            buckets.append(current)
            current += resolution

    # Build cumulative usage per meter
    meter_cumulative = {}
    for meter_id, readings in meter_data_usage.items():
        baseline = readings[0]["reading_kwh"]
        time_series = {}
        j = 0
        last_value = baseline
        for bucket in buckets:
            if query_type in ["past_week", "past_month"]:
                while j < len(readings) and readings[j]["timestamp"].date() <= bucket:
                    last_value = readings[j]["reading_kwh"]
                    j += 1
            else:
                while j < len(readings) and readings[j]["timestamp"] <= bucket:
                    last_value = readings[j]["reading_kwh"]
                    j += 1
            time_series[bucket] = last_value - baseline
        meter_cumulative[meter_id] = time_series

    # Sum the usage across all meters
    aggregated_cumulative = {}
    for bucket in buckets:
        total = 0
        for meter_id in meter_cumulative:
            total += meter_cumulative[meter_id].get(bucket, 0)
        aggregated_cumulative[bucket] = total

    # Prepare x_values and y_values
    if query_type in ["past_week", "past_month"]:
        x_values = [bucket.strftime("%Y-%m-%d") for bucket in buckets]
    else:
        x_values = [bucket.strftime("%Y-%m-%d %H:%M") for bucket in buckets]

    y_values = [aggregated_cumulative[bucket] for bucket in buckets]

    # For "last_30_min", we want a single bar representing the total usage over that 30 min window
    if query_type == "last_30_min":
        total_usage = y_values[-1] if y_values else 0
        x_values = ["Last 30 Minutes"]
        y_values = [total_usage]
    else:
        # Otherwise, total usage is just the final cumulative point
        total_usage = y_values[-1] if y_values else 0

    # Create the bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_values, y=y_values, name="Electricity Usage"))
    fig.update_layout(
        title="Electricity Consumption Over Selected Period",
        xaxis_title="Time" if query_type not in ["past_week", "past_month"] else "Date",
        yaxis_title="Cumulative Usage (kWh)",
        template="plotly_white"
    )

    result_text = f"Electricity usage: {total_usage} kWh (aggregated from {len(meter_cumulative)} meter(s))"
    return result_text, fig

# rules for meter reading_1(this one is for data transfer API, meter_data)
#HOYT PLS CHECK HERE
@app.callback(
    Output('message', 'children'),
    Input('submit-btn', 'n_clicks'),
    [State('meter_id', 'value'),
     State('timestamp', 'value'),
     State('reading_kwh', 'value')]
)
def submit_reading(n_clicks, meter_id, timestamp, reading_kwh):
    if n_clicks > 0 and meter_id and timestamp and reading_kwh is not None:
        try:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return "Invalid Timestamp Format Use YYYY-MM-DDTHH:MM:SS"
        
        result = write_to_meter_data(meter_id, timestamp, reading_kwh)

        if "Error" not in result:
            data_store.append({"meter_id": meter_id, "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                               "reading_kwh": reading_kwh})

        return result 
    
    return "Please fill all fields"


# rules for meter reading_2(this one is for data display)
#HOYT PLS CHECK HERE
@app.callback(
    Output('data-display', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_data(n):
    if not data_store:
        return "No data available"

    # create DataFrame
    df = pd.DataFrame(data_store)

    # generate a table for uploaded data(data_store)
    return html.Table([
        html.Tr([html.Th(col) for col in df.columns])
    ] + [
        html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))
    ])

# rule for shut down
# open new page 1st, then actual shut down
@app.callback(
    Output("shutdown-message", "children"),
    Input("btn-shutdown", "n_clicks"),
    prevent_initial_call=True
)
def execute_shutdown(n_clicks):
    if n_clicks > 0:
        import threading
        threading.Thread(target=shutdown_server).start()
    return ""

#change pages
@app.callback(
    Output("page-content", "children"),
    [Input("btn-user-reg", "n_clicks"),
     Input("btn-user-query", "n_clicks"),
     Input("btn-gov-query", "n_clicks"),
     Input("btn-meter-read", "n_clicks"),
     Input("btn-shutdown", "n_clicks")]
)
def update_page(btn_user, btn_query, btn_gov, btn_meter, btn_shutdown):
    ctx = dash.callback_context

    if not ctx.triggered:
        return html.Div("Welcome! Please select an option.")

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if triggered_id == "btn-user-reg":
        return user_registration_page()
    elif triggered_id == "btn-user-query":
        return user_query_page()
    elif triggered_id == "btn-gov-query":
        return government_query_page()
    elif triggered_id == "btn-meter-read":
        return meter_reading_page()
    elif triggered_id == "btn-shutdown":
        threading.Thread(target=shutdown_server).start()
        return shutdown_page()

    return html.Div("404 - Page Not Found")

#for data cleaning on monthly basis
@app.callback(
    Output("aggregate-result", "children"),
    Input("aggregate-btn", "n_clicks"),
    prevent_initial_call=True
)
def trigger_aggregation(n_clicks):
    result = aggregate_meter_data()
    return result






# ↓ Main Fucnction, App Execution ↓
if __name__ == '__main__':
    registration_data_location = "Registration.json"
    meter_data_location = "meter_data.json"
    meter_data, registration_data = read_json_files(meter_data_location, registration_data_location)
    data_store = []
    for meter_id in meter_data:
        for entry in meter_data[meter_id]:
            entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")
    app.run_server(port=6666, debug=True)