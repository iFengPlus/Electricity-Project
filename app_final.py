import dash
from dash import html, dcc, Input, Output, State, ctx
import pandas as pd
import plotly.graph_objects as go
import os
import threading
from datetime import datetime, timedelta
import json
import time

# change format of time in meter_data
def format_meter_data():
    
    global meter_data  

    for meter_id in meter_data:
        for entry in meter_data[meter_id]:
            if isinstance(entry["timestamp"], str): 
                entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")


def read_json_files(meter_data_path, registration_path):
    try:
        # 加载 meter_data
        if os.path.exists(meter_data_path):
            with open(meter_data_path, 'r', encoding='utf-8') as file:
                meter_data = json.load(file) or {}  # 读取失败就返回空字典
        else:
            meter_data = {}

        # 加载 registration_data
        if os.path.exists(registration_path):
            with open(registration_path, 'r', encoding='utf-8') as file:
                registration_data = json.load(file) or {"registered_users": {}, "unregistered_meters": {}}
        else:
            registration_data = {"registered_users": {}, "unregistered_meters": {}}

        return meter_data, registration_data

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {}, {"registered_users": {}, "unregistered_meters": {}}




# Use depends on situation, already load data when prog start


def save_user(data):
    with open(registration_data_location, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_meter(data):
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
        html.Button("Server Shut Down", id="btn-shutdown", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'red', 'color': 'white'}),
    ], style={'textAlign': 'center'}),

    html.Hr(),  # 分割线

    # 🔹 预定义 `btn-back`，避免 Dash 报错（默认隐藏）
    html.Button("Back", id="btn-back", n_clicks=0, style={'display': 'none'}),

    # 🔹 这里动态切换子页面
    html.Div(id="page-content", style={'padding': '20px'}),

    # 🔹 隐藏的 Location 组件，用于网页关闭
    dcc.Location(id='shutdown-url', refresh=True),

    html.Div(id="shutdown-message")  # 用于显示关闭消息
    
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
    global meter_data  # 确保修改全局变量

    # **✅ 确保 timestamp 是 datetime 类型**
    if isinstance(timestamp, str):
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

    # **✅ 确保 meter_id 存在**
    if meter_id not in meter_data:
        meter_data[meter_id] = []

    # **✅ 确保 meter_data 里的时间戳是 datetime 类型**
    for entry in meter_data[meter_id]:
        if isinstance(entry["timestamp"], str):
            entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")

    # **✅ 检查是否已经存在相同时间戳**
    for entry in meter_data[meter_id]:
        if entry["timestamp"] == timestamp:
            return "❌ Error: Duplicate timestamp. Data not inserted."

    # **✅ 找到插入位置**
    index = 0
    while index < len(meter_data[meter_id]) and meter_data[meter_id][index]["timestamp"] < timestamp:
        index += 1

    # **✅ 插入数据**
    meter_data[meter_id].insert(index, {"timestamp": timestamp, "reading_kwh": reading_kwh})
    return "✅ Data inserted successfully!"

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



# after-shoutdown page layout
def shutdown_page():
    return html.Div(
        style={"textAlign": "center", "fontSize": "24px", "marginTop": "10%"},  # ✅ 进一步向上调整位置
        children=[
            "Now is 0:00 lah! Server also need a rest🌙", html.Br(), html.Br(),
            "Good Night!\xa0\xa0\xa0\xa0晚安!\xa0\xa0\xa0\xa0Selamat Malam!\xa0\xa0\xa0\xa0இனிய இரவு!"
        ]
    )


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

    print("📌 当前 registered_users:", registration_data["registered_users"])  # ✅ 打印数据

    with lock:
        # ✅ **检查 userID 是否已绑定其他 meter**
        if user_id in registration_data["registered_users"]:
            return f"Error: userID {user_id} is already bound to another meter."

        # ✅ **查找 meterID 是否已经被注册**
        existing_user = next(
            (uid for uid, data in registration_data["registered_users"].items() if data.get("meterID") == meter_id),
            None
        )

        print(f"🔍 搜索 meterID {meter_id}，找到用户ID: {existing_user}")  # ✅ 打印搜索结果

        if existing_user:
            # ✅ **解绑旧 userID，绑定新 userID**
            registration_data["registered_users"][user_id] = registration_data["registered_users"].pop(existing_user)
            save_user(registration_data)
            return "Binding Successful!"

        # ✅ **查找 meterID 是否在 `unregistered_meters`**
        elif meter_id in registration_data["unregistered_meters"]:
            meter_info = registration_data["unregistered_meters"].pop(meter_id)  # 取出 meter 数据
            meter_info["meterID"] = meter_id  # **确保 meterID 也存入**
            registration_data["registered_users"][user_id] = meter_info  # **绑定到用户**
            save_user(registration_data)
            return "Binding Successful!"

        # ❌ **meterID 不存在**
        return f"Error: meterID {meter_id} not found."

    return "Error: Unexpected issue occurred."





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
        format_meter_data() 
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
            start_time = max((r["timestamp"] for r in readings if now.replace(hour=0, minute=0, second=0) - timedelta(days=1) <= r["timestamp"] < now.replace(hour=0, minute=0, second=0)),
            default=now.replace(hour=0, minute=0, second=0) - timedelta(days=1))
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

    format_meter_data() 
    latest_timestamp = max(r["timestamp"] for r in readings)
    now = latest_timestamp
    results = {}
    

    # 过滤时间段
    if query_type == "last_30_min":
        start_time = now - timedelta(minutes=30)
    elif query_type == "today":
            start_time = max((r["timestamp"] for r in readings if now.replace(hour=0, minute=0, second=0) - timedelta(days=1) <= r["timestamp"] < now.replace(hour=0, minute=0, second=0)),
            default=now.replace(hour=0, minute=0, second=0) - timedelta(days=1))
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







if __name__ == '__main__':
    registration_data_location = "Registration.json"
    meter_data_location = "meter_data.json"
    meter_data, registration_data = read_json_files(meter_data_location, registration_data_location)
    data_store = []
    for meter_id in meter_data:
        for entry in meter_data[meter_id]:
            entry["timestamp"] = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")
    app.run_server(port=6666, debug=True)