import csv
from datetime import datetime
import threading
import time
from flask import Flask, jsonify, render_template, request
import webview

app = Flask(__name__)

# Global Sensor & Automation State
sensor_data = {
    "dhtConnected": False,
    "soilConnected": False,
    "lightConnected": False,
    "temp": 0.0,
    "hum": 0.0,
    "soil": 0,
    "light": 0,
    "pump": False,
    "lightState": False,
    "fan": False,
}

last_update_time = 0

def log_to_csv(temp, hum, soil, light, pump, light_state, fan):
    """Logs real-time data or 'ERR' to sensor_data.csv every 2 seconds"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, temp, hum, soil, light, pump, light_state, fan]

    with open("sensor_data.csv", mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            writer.writerow([
                "Timestamp", "Temperature_C", "Humidity_pct",
                "Soil_Moisture_pct", "Light_Lux", "Pump_Active",
                "Grow_Light_Active", "Exhaust_Fan_Active",
            ])
        writer.writerow(row)

def background_logging():
    """Background loop exclusively for CSV logging and timeout detection"""
    global sensor_data, last_update_time
    while True:
        time.sleep(2)
        
        # If we haven't received an update from the ESP32 in 5 seconds, mark as disconnected
        if time.time() - last_update_time > 5:
            sensor_data["dhtConnected"] = False
            sensor_data["soilConnected"] = False
            sensor_data["lightConnected"] = False

        # Save record to CSV log file
        log_to_csv(
            sensor_data["temp"] if sensor_data["dhtConnected"] else "ERR",
            sensor_data["hum"] if sensor_data["dhtConnected"] else "ERR",
            sensor_data["soil"] if sensor_data["soilConnected"] else "ERR",
            sensor_data["light"] if sensor_data["lightConnected"] else "ERR",
            sensor_data["pump"],
            sensor_data["lightState"],
            sensor_data["fan"],
        )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/sensors")
def api_sensors():
    return jsonify(sensor_data)

@app.route("/api/toggle/<sensor_name>")
def toggle_sensor(sensor_name):
    global sensor_data
    if sensor_name == "dht":
        sensor_data["dhtConnected"] = not sensor_data["dhtConnected"]
    elif sensor_name == "soil":
        sensor_data["soilConnected"] = not sensor_data["soilConnected"]
    elif sensor_name == "light":
        sensor_data["lightConnected"] = not sensor_data["lightConnected"]
    return jsonify(sensor_data)

# --- NEW ROUTE: Receives live JSON from the physical ESP32 ---
@app.route("/update", methods=["POST"])
def update_from_esp32():
    global sensor_data, last_update_time
    data = request.json
    
    if data:
        last_update_time = time.time()
        
        # Map ESP32 JSON keys to Flask dictionary keys
        sensor_data["temp"] = data.get("temperature", 0.0)
        sensor_data["hum"] = data.get("humidity", 0.0)
        sensor_data["soil"] = data.get("soil_moisture", 0)
        
        # Convert "ON"/"OFF" strings from ESP32 to Booleans for Flask UI
        sensor_data["fan"] = (data.get("fan") == "ON")
        sensor_data["pump"] = (data.get("water_pump") == "ON")
        sensor_data["lightState"] = (data.get("light") == "ON")
        
        # Mark sensors as actively connected because data arrived
        sensor_data["dhtConnected"] = True
        sensor_data["soilConnected"] = True
        sensor_data["lightConnected"] = True
        
    return jsonify({"status": "success"})

def run_flask():
    # host="0.0.0.0" allows the ESP32 to connect over Wi-Fi. Port changed to 8000.
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    log_thread = threading.Thread(target=background_logging, daemon=True)
    log_thread.start()

    webview.create_window(
        "Automated ESP32 Greenhouse for Pechay",
        "http://127.0.0.1:8000",
        width=1400,
        height=850,
        background_color="#030a07",
    )
    webview.start()