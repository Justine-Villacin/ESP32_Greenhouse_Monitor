from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Store the latest sensor readings
sensor_data = {
    "temperature": 0.0,
    "humidity": 0.0,
    "soil_moisture": 0,
    "fan": "OFF",
    "water_pump": "OFF",
    "light": "OFF"
}

class SensorData(BaseModel):
    temperature: float
    humidity: float
    soil_moisture: int
    fan: str
    water_pump: str
    light: str

@app.post("/update")
async def update_data(data: SensorData):
    global sensor_data
    sensor_data = data.model_dump()
    return {"status": "success"}

@app.get("/data")
async def get_data():
    return sensor_data

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IoT Greenhouse Dashboard</title>
        <style>
            body {
                margin: 0;
                min-height: 100vh;
                background: linear-gradient(135deg, #0f52ba, #ff8c00);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #ffffff;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .glass-panel {
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                padding: 35px;
                width: 85%;
                max-width: 400px;
                box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);
            }
            h1 {
                text-align: center;
                font-size: 1.4rem;
                margin-bottom: 25px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            .metric {
                display: flex;
                justify-content: space-between;
                padding: 14px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.15);
                font-size: 1.1rem;
            }
            .metric:last-child { border-bottom: none; }
            .val { font-weight: bold; }
        </style>
        <script>
            async function fetchData() {
                try {
                    const response = await fetch('/data');
                    const data = await response.json();
                    document.getElementById('temp').innerText = data.temperature.toFixed(1) + ' CELSIUS';
                    document.getElementById('hum').innerText = data.humidity.toFixed(0) + '%';
                    document.getElementById('soil').innerText = data.soil_moisture + '%';
                    document.getElementById('fan').innerText = data.fan;
                    document.getElementById('pump').innerText = data.water_pump;
                    document.getElementById('light').innerText = data.light;
                } catch (error) { console.error("Error fetching data"); }
            }
            setInterval(fetchData, 2000); 
            window.onload = fetchData;
        </script>
    </head>
    <body>
        <div class="glass-panel">
            <h1>Greenhouse Monitor</h1>
            <div class="metric"><span>TEMPERATURE</span> <span id="temp" class="val">-- CELSIUS</span></div>
            <div class="metric"><span>HUMIDITY</span> <span id="hum" class="val">--%</span></div>
            <div class="metric"><span>SOIL MOISTURE</span> <span id="soil" class="val">--%</span></div>
            <div class="metric"><span>FAN</span> <span id="fan" class="val">--</span></div>
            <div class="metric"><span>WATER PUMP</span> <span id="pump" class="val">--</span></div>
            <div class="metric"><span>LIGHT</span> <span id="light" class="val">--</span></div>
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)