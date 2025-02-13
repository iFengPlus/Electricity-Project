#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Updated on Tue Feb 13 2025

@author: gaoyidi
"""

import json
import datetime
import dash
from dash import dcc, html, Input, Output, State, ctx
import plotly.graph_objects as go

# Load user and meter data
with open("predataset.json", "r") as f:
    user_data = json.load(f)

with open("meter_data.json", "r") as f:
    meter_data = json.load(f)

for meter_id in meter_data:
    for entry in meter_data[meter_id]:
        entry["timestamp"] = datetime.datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")

app = dash.Dash(__name__)

# Updated layout (removed password field)
app.layout = html.Div([
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
        html.Div(id="query-result"),
        dcc.Graph(id="usage-graph"),
    ], id="query-section", style={"display": "none"}),
])

# Helper function to find closest timestamp reading
def get_reading_at(readings, target_time):
    readings_sorted = sorted(readings, key=lambda x: abs(x["timestamp"] - target_time))
    return readings_sorted[0]["reading_kwh"] if readings_sorted else None

# Handle login and queries
@app.callback(
    [Output("login-status", "children"), 
     Output("query-section", "style"),
     Output("query-result", "children"), 
     Output("usage-graph", "figure")],
    [Input("login-btn", "n_clicks"), 
     Input("query-btn", "n_clicks")],
    [State("user-id", "value"), State("query-type", "value")]
)
def handle_callbacks(login_clicks, query_clicks, user_id, query_type):
    triggered_id = ctx.triggered_id  

    # User Login (only checks userID, no password required)
    if triggered_id == "login-btn":
        user = next((u for u in user_data if u["userID"] == user_id), None)
        if user:
            return (f"Login successful! Meter ID: {user['meterID']}", 
                    {"display": "block"}, "", go.Figure())
        else:
            return ("❌ User not found. Please enter a valid User ID.", 
                    {"display": "none"}, "", go.Figure())

    # Query electricity usage
    elif triggered_id == "query-btn":
        user = next((u for u in user_data if u["userID"] == user_id), None)
        if not user:
            return ("❌ User not found.", {"display": "none"}, "No user data available.", go.Figure())

        meter_id = user["meterID"]
        if meter_id not in meter_data:
            return ("⚠️ No electricity data found.", {"display": "block"}, "No data for this meter.", go.Figure())

        readings = meter_data[meter_id]
        latest_timestamp = max(r["timestamp"] for r in readings) 
        now = latest_timestamp
        results = {}

        # Filter readings based on query type
        if query_type == "last_30_min":
            start_time = now - datetime.timedelta(minutes=30)
        elif query_type == "today":
            start_time = now.replace(hour=0, minute=0, second=0)
        elif query_type == "yesterday":
            start_time = now - datetime.timedelta(days=1)
            end_time = start_time + datetime.timedelta(hours=24)
        elif query_type == "past_week":
            start_time = now - datetime.timedelta(days=7)
        elif query_type == "past_month":
            start_time = now - datetime.timedelta(days=30)

        # Apply filtering
        filtered_readings = [r for r in readings if r["timestamp"] >= start_time]
        if query_type == "yesterday":
            filtered_readings = [r for r in readings if start_time <= r["timestamp"] < end_time]

        if not filtered_readings:
            return ("⚠️ No Data Available", {"display": "block"}, "No electricity data found for this period.", go.Figure())

        # Calculate electricity usage
        results["usage"] = get_reading_at(filtered_readings, max(r["timestamp"] for r in filtered_readings)) - \
                           get_reading_at(filtered_readings, min(r["timestamp"] for r in filtered_readings))

        # Create graph
        timestamps = [r["timestamp"] for r in filtered_readings]
        consumption = [r["reading_kwh"] for r in filtered_readings]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=timestamps, y=consumption, mode="lines+markers", name="Electricity Usage"))
        fig.update_layout(title="Electricity Consumption Over Selected Period",
                          xaxis_title="Time", yaxis_title="Usage (kWh)",
                          xaxis=dict(showgrid=True), yaxis=dict(showgrid=True),
                          template="plotly_white")

        return (f"⚡ Electricity usage: {results['usage']} kWh", {"display": "block"}, "", fig)

    return ("", {"display": "none"}, "", go.Figure())

if __name__ == "__main__":
    app.run_server(debug=True, port=8056)
