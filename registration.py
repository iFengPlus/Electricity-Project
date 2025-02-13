from flask import Flask, request, jsonify, render_template
import json
import os
import threading
from datetime import datetime

app = Flask(__name__, template_folder="templates")
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

@app.route('/', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/check_meter', methods=['GET'])
def check_meter():
    meter_id = request.args.get("meterID")
    if not meter_id:
        return jsonify({"error": "meterID is required"}), 400

    data = load_data()
    for record in data:
        if record["meterID"] == meter_id:
            return jsonify({"status": "available" if record["userID"] == "NA" else "already_engaged"}), 200

    return jsonify({"error": "meterID not found"}), 404

@app.route('/verify_password', methods=['POST'])
def verify_password():
    request_data = request.json
    meter_id = request_data.get("meterID")
    password = request_data.get("password")

    if not meter_id or not password:
        return jsonify({"error": "meterID and password are required"}), 400

    data = load_data()
    for record in data:
        if record["meterID"] == meter_id:
            if record["password"] == password:
                return jsonify({"message": "Password verified"}), 200
            else:
                return jsonify({"error": "Invalid password"}), 200

    return jsonify({"error": "meterID not found"}), 404

@app.route('/check_userid', methods=['GET'])
def check_user():
    user_id = request.args.get("userID")
    meter_id = request.args.get("meterID")

    if not user_id:
        return jsonify({"error": "userID is required"}), 400

    data = load_data()
    for record in data:
        if record["userID"] == user_id and record["meterID"] != meter_id:
            return jsonify({"exists": True})

    return jsonify({"exists": False})

@app.route('/bind', methods=['POST'])
def bind_meter():
    if request.is_json:
        request_data = request.json
        meter_id = request_data.get("meterID")
        user_id = request_data.get("userID")
        password = request_data.get("password")
        old_password = request_data.get("old_password", None)
    else:
        meter_id = request.form.get("meterID")
        user_id = request.form.get("userID")
        password = request.form.get("password")
        old_password = request.form.get("old_password", None)

    if not meter_id or not user_id or not password:
        return jsonify({"error": "meterID, userID, and password are required"}), 400

    with lock:
        data = load_data()
        for record in data:
            if record["meterID"] == meter_id:
                if record["userID"] == "NA":
                    for rec in data:
                        if rec["userID"] == user_id and rec["meterID"] != meter_id:
                            return jsonify({"error": "userID already exists, choose another"}), 409

                    record["userID"] = user_id
                    record["password"] = password
                    record["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    save_data(data)
                    return "<h2>Binding Successful</h2>", 200
                else:
                    if not old_password:
                        return "<h2>Error: Old password required</h2>", 403
                    if record["password"] != old_password:
                        return "<h2>Error: Invalid old password</h2>", 401

                    for rec in data:
                        if rec["userID"] == user_id and rec["meterID"] != meter_id:
                            return jsonify({"error": "userID already exists, choose another"}), 409

                    record["userID"] = user_id
                    record["password"] = password
                    record["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    save_data(data)
                    return "<h2>Update Successful</h2>", 200

        return "<h2>Error: meterID not found</h2>", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
