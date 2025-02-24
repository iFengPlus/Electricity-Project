import dash
from dash import html, dcc, Input, Output, State, ctx
import pandas as pd
import plotly.graph_objects as go
import os
import threading
from datetime import datetime, timedelta
import json
import time

# ✅ 读取 & 保存 JSON 数据
def read_json_files(meter_data_path, registration_path):
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


def save_meter(data):
    # 确保时间格式转换后存入 JSON
    for meter_id in data:
        for entry in data[meter_id]:
            if isinstance(entry["timestamp"], datetime):
                entry["timestamp"] = entry["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")

    with open(meter_data_location, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ✅ **新增 Meter Data Aggregation API**
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
            
            # 计算该月总 kWh
            if month_key not in monthly_totals:
                monthly_totals[month_key] = 0
            monthly_totals[month_key] += entry["reading_kwh"]

        # 存储汇总后的数据
        aggregated_data[meter_id] = [
            {"timestamp": f"{month_key}-01T00:00:00", "reading_kwh": total}
            for month_key, total in monthly_totals.items()
        ]

    # 覆盖原 `meter_data`，只保留按月汇总的数据
    meter_data = aggregated_data

    # 保存数据
    save_meter(meter_data)
    return "✅ Aggregation completed! Monthly data saved."


# ✅ **Dash App 代码**
app = dash.Dash(__name__, suppress_callback_exceptions=True)
lock = threading.Lock()

# ✅ **主页面 Layout（保留原有功能）**
app.layout = html.Div([
    html.H1("Smart Meter Management System", style={'textAlign': 'center'}),

    # ✅ **新增聚合按钮（不会影响其他页面功能）**
    html.Div([
        html.Button("Aggregate Meter Data", id="aggregate-btn", n_clicks=0, style={'margin': '10px'}),
        html.Div(id="aggregate-result", style={'color': 'green', 'margin': '10px'})
    ], style={'textAlign': 'center'}),

    # ✅ 原有按钮
    html.Div([
        html.Button("User Registration", id="btn-user-reg", n_clicks=0, style={'margin': '5px'}),
        html.Button("User Query", id="btn-user-query", n_clicks=0, style={'margin': '5px'}),
        html.Button("Government Query", id="btn-gov-query", n_clicks=0, style={'margin': '5px'}),
        html.Button("Meter Reading", id="btn-meter-read", n_clicks=0, style={'margin': '5px'}),
        html.Button("Server Shut Down", id="btn-shutdown", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'red', 'color': 'white'}),
    ], style={'textAlign': 'center'}),

    html.Hr(),  # 分割线

    html.Div(id="shutdown-message")
])


# ✅ **Dash 回调，监听聚合按钮点击**
@app.callback(
    Output("aggregate-result", "children"),
    Input("aggregate-btn", "n_clicks"),
    prevent_initial_call=True
)
def trigger_aggregation(n_clicks):
    result = aggregate_meter_data()
    return result


# ✅ **Dash 回调：页面导航（保持原有功能）**
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


# ✅ **运行 Dash 服务器**
if __name__ == '__main__':
    registration_data_location = "Registration.json"
    meter_data_location = "meter_data.json"
    meter_data, registration_data = read_json_files(meter_data_location, registration_data_location)

    app.run_server(port=8050, debug=True)
