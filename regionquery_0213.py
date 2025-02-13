#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 20:51:34 2025

@author: chingpan
"""

import json
import datetime
import dash
from dash import dcc, html, Input, Output, State, ctx
import plotly.graph_objects as go

with open("predataset.json", "r") as f:
    user_data = json.load(f)

with open("meter_data.json", "r") as f:
    meter_data = json.load(f)

for meter_id in meter_data:
    for entry in meter_data[meter_id]:
        entry["timestamp"] = datetime.datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S")

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Electricity Usage Query System"),
    html.Label("Select Region:"),
    dcc.Dropdown(
        id="region-dropdown",
        options=[{"label": reg, "value": reg} for reg in sorted(set(u["region"] for u in user_data))],
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
    html.Div(id="query-result"),
    dcc.Graph(id="usage-graph"),
])

def get_reading_at(readings, target_time):
    readings_sorted = sorted(readings, key=lambda x: abs(x["timestamp"] - target_time))
    return readings_sorted[0]["reading_kwh"] if readings_sorted else None

@app.callback(
    Output("area-dropdown", "options"),
    Input("region-dropdown", "value")
)
def update_area_options(selected_region):
    if selected_region:
        areas = sorted(set(u["area"] for u in user_data if u["region"] == selected_region))
        return [{"label": area, "value": area} for area in areas]
    return []

@app.callback(
    [Output("query-result", "children"), Output("usage-graph", "figure")],
    Input("query-btn", "n_clicks"),
    [State("region-dropdown", "value"), State("area-dropdown", "value"), State("query-type", "value")]
)
def query_data(n_clicks, region, area, query_type):
    if not (region and area and query_type):
        return "Please select region, area, and time period.", go.Figure()

    meter_ids = [u["meterID"] for u in user_data if u["region"] == region and u["area"] == area]
    readings = [r for m in meter_ids if m in meter_data for r in meter_data[m]]
    
    if not readings:
        return "No data found for this selection.", go.Figure()

    latest_timestamp = max(r["timestamp"] for r in readings)
    now = latest_timestamp
    results = {}

    filtered_readings = []
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


if __name__ == "__main__":
    app.run_server(debug=True, port=8054)
