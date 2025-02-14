import dash
from dash import html, dcc, Input, Output, State, ctx
import pandas as pd
import plotly.graph_objects as go
import os
import threading
from datetime import datetime, timedelta
import json



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


# Use depends on situation, already load data when prog start
DATA_FILE = "Registration.json"
def load_data():
    #load Reg
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        return json.loads(content) if content else []

def save_data(data):
    #load Registration data
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Helper function to find closest timestamp reading
def get_reading_at(readings, target_time):
    readings_sorted = sorted(readings, key=lambda x: abs(x["timestamp"] - target_time))
    return readings_sorted[0]["reading_kwh"] if readings_sorted else None   


app = dash.Dash(__name__, suppress_callback_exceptions=True)
lock = threading.Lock()
# 主页面 Layout
app.layout = html.Div([
    html.H1("Smart Meter Management System", style={'textAlign': 'center'}),

    # 🔹 导航栏（按钮切换页面）
    html.Div([
        html.Button("User Registration", id="btn-user-reg", n_clicks=0, style={'margin': '5px'}),
        html.Button("User Query", id="btn-user-query", n_clicks=0, style={'margin': '5px'}),
        html.Button("Government Query", id="btn-gov-query", n_clicks=0, style={'margin': '5px'}),
        html.Button("Meter Reading", id="btn-meter-read", n_clicks=0, style={'margin': '5px'}),
    ], style={'textAlign': 'center'}),

    html.Hr(),  # 分割线

    # 🔹 预定义 `btn-back`，避免 Dash 报错（默认隐藏）
    html.Button("Back", id="btn-back", n_clicks=0, style={'display': 'none'}),

    # 🔹 这里动态切换子页面
    html.Div(id="page-content", style={'padding': '20px'})
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

        # 🔹 返回按钮
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
        
        # 选择地区
        html.Label("Select Region:"),
        dcc.Dropdown(
            id="region-dropdown",
            options=[{"label": reg, "value": reg} for reg in sorted(set(u["region"] for u in registration_data))],
            placeholder="Select Region"
        ),

        # 选择区域
        html.Label("Select Area:"),
        dcc.Dropdown(id="area-dropdown", placeholder="Select Area"),

        # 选择时间段
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
    """
    更新 meter_data，将新的电表读数写入相应的 Meter ID 下。
    """
    global meter_data  # 确保修改全局变量

    # 确保 meter_id 存在
    if meter_id not in meter_data:
        meter_data[meter_id] = []

    # 添加新读数
    meter_data[meter_id].append({
        "timestamp": timestamp,
        "reading_kwh": reading_kwh
    })

# Meter reading page
def meter_reading_page():
    return html.Div([
        html.H1("Meter Readings"),
        
        # 用户输入
        dcc.Input(id='meter_id', type='text', placeholder='Enter Meter ID'),
        dcc.Input(id='timestamp', type='text', placeholder='Enter Timestamp (YYYY-MM-DDTHH:MM:SS)'),
        dcc.Input(id='reading_kwh', type='number', placeholder='Enter kWh Reading'),
        
        # 提交按钮
        html.Button('Submit', id='submit-btn', n_clicks=0),
        
        # 消息反馈
        html.Div(id='message'),

        # 数据自动刷新
        dcc.Interval(id='interval-component', interval=2000, n_intervals=0),

        # 数据展示
        html.Div(id='data-display'),

        # 返回主页按钮
        html.Button("Back", id="btn-back", n_clicks=0, style={'margin-top': '10px'})
    ])


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

    # 用户登录
    if triggered_id == "login-btn":
        user = next((u for u in registration_data if u["userID"] == user_id), None)
        if user:
            return (f"Login successful! Meter ID: {user['meterID']}", 
                    {"display": "block"}, "", go.Figure())
        else:
            return ("❌ User not found. Please enter a valid User ID.", 
                    {"display": "none"}, "", go.Figure())

    # 查询电力使用
    elif triggered_id == "query-btn":
        user = next((u for u in registration_data if u["userID"] == user_id), None)
        if not user:
            return ("❌ User not found.", {"display": "none"}, "No user data available.", go.Figure())

        meter_id = user["meterID"]
        if meter_id not in meter_data:
            return ("⚠️ No electricity data found.", {"display": "block"}, "No data for this meter.", go.Figure())

        readings = meter_data[meter_id]
        latest_timestamp = max(r["timestamp"] for r in readings) 
        now = latest_timestamp
        results = {}

        # 过滤时间段
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

        if not filtered_readings:
            return ("⚠️ No Data Available", {"display": "block"}, "No electricity data found for this period.", go.Figure())

        # 计算电力使用量
        results["usage"] = get_reading_at(filtered_readings, max(r["timestamp"] for r in filtered_readings)) - \
                           get_reading_at(filtered_readings, min(r["timestamp"] for r in filtered_readings))

        # 绘制图表
        timestamps = [r["timestamp"] for r in filtered_readings]
        consumption = [r["reading_kwh"] for r in filtered_readings]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=timestamps, y=consumption, mode="lines+markers", name="Electricity Usage"))
        fig.update_layout(title="Electricity Consumption Over Selected Period",
                          xaxis_title="Time", yaxis_title="Usage (kWh)",
                          template="plotly_white")

        return (f"⚡ Electricity usage: {results['usage']} kWh", {"display": "block"}, "", fig)

    return ("", {"display": "none"}, "", go.Figure())

#rules for government query_1
@app.callback(
    [Output("area-dropdown", "options")],
    Input("region-dropdown", "value")
)
def update_area_options(selected_region):
    if selected_region:
        areas = sorted(set(u["area"] for u in registration_data if u["region"] == selected_region))
        return [[{"label": area, "value": area} for area in areas]]
    return [[]]


#rules for government query_2
@app.callback(
    [Output("gov-query-result", "children"), Output("gov-usage-graph", "figure")],
    Input("query-btn", "n_clicks"),
    [State("region-dropdown", "value"), State("area-dropdown", "value"), State("query-type", "value")]
)
def query_data(n_clicks, region, area, query_type):
    if not (region and area and query_type):
        return "Please select region, area, and time period.", go.Figure()

    meter_ids = [u["meterID"] for u in registration_data if u["region"] == region and u["area"] == area]
    readings = [r for m in meter_ids if m in meter_data for r in meter_data[m]]
    
    if not readings:
        return "No data found for this selection.", go.Figure()

    latest_timestamp = max(r["timestamp"] for r in readings)
    now = latest_timestamp
    results = {}

    # 过滤时间段
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

    if query_type == "yesterday":
        filtered_readings = [r for r in readings if start_time <= r["timestamp"] < end_time]
    else:
        filtered_readings = [r for r in readings if r["timestamp"] >= start_time]

    if not filtered_readings:
        return ("⚠️ No Data Available", go.Figure())

    results["usage"] = get_reading_at(filtered_readings, max(r["timestamp"] for r in filtered_readings)) - \
                       get_reading_at(filtered_readings, min(r["timestamp"] for r in filtered_readings))

    timestamps = [r["timestamp"] for r in filtered_readings]
    consumption = [r["reading_kwh"] for r in filtered_readings]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=consumption, mode="lines+markers", name="Electricity Usage"))

    fig.update_layout(
        title="Electricity Consumption Over Selected Period",
        xaxis_title="Time",
        yaxis_title="Usage (kWh)",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        template="plotly_white"
    )

    return (f"⚡ Electricity usage: {results['usage']} kWh", fig)



# rules for meter reading_1
@app.callback(
    Output('message', 'children'),
    Input('submit-btn', 'n_clicks'),
    [State('meter_id', 'value'),
     State('timestamp', 'value'),
     State('reading_kwh', 'value')]
)
def submit_reading(n_clicks, meter_id, timestamp, reading_kwh):
    if n_clicks > 0 and meter_id and timestamp and reading_kwh is not None:
        # **校验时间格式**
        try:
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return "❌ Invalid Timestamp Format! Use YYYY-MM-DDTHH:MM:SS"
        
        # **存入 data_store（Dash 显示用）**
        data_store.append({"meter_id": meter_id, "timestamp": timestamp, "reading_kwh": reading_kwh})
        
        # **存入 meter_data（主数据）**
        write_to_meter_data(meter_id, timestamp, reading_kwh)

        return "✅ Data submitted successfully!"
    
    return "⚠️ Please fill all fields!"

# rules for meter reading_2
@app.callback(
    Output('data-display', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_data(n):
    if not data_store:
        return "No data available"

    # 创建 DataFrame
    df = pd.DataFrame(data_store)

    # 生成 HTML 表格
    return html.Table([
        html.Tr([html.Th(col) for col in df.columns])
    ] + [
        html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))
    ])

#change pages
@app.callback(
    Output("page-content", "children"),
    [
        Input("btn-user-reg", "n_clicks"),
        Input("btn-user-query", "n_clicks"),
        Input("btn-gov-query", "n_clicks"),
        Input("btn-meter-read", "n_clicks"),
        Input("btn-back", "n_clicks")
    ],
    prevent_initial_call=True
)
def update_page(user_reg_clicks, user_query_clicks, gov_query_clicks, meter_read_clicks, back_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return html.Div()
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "btn-user-reg":
        return user_registration_page()
    elif trigger_id == "btn-user-query":
        return user_query_page()
    elif trigger_id == "btn-gov-query":
        return government_query_page()
    elif trigger_id == "btn-meter-read":
        return meter_reading_page()
    elif trigger_id == "btn-back":
        return html.Div()
    return html.Div()


if __name__ == '__main__':
    meter_data, registration_data = read_json_files("meter_data.json", "Registration.json")
    data_store = []
    for meter_id in meter_data:
        for entry in meter_data[meter_id]:
            entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")
    app.run_server(port=6666, debug=True)