#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// Libraries for disabling the brownout detector
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

const char* ssid = "Delinia Fam 2.4G";
const char* password = "03121980";
const char* serverName = "http://192.168.100.217:8000/update"; 

#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// Define the Soil Moisture Sensor pin (Use ADC1 pins like 34, 35, 36, 39)
#define SOIL_MOISTURE_PIN 34 

// --- Soil sensor calibration + disconnect detection ---
// GPIO34-39 are INPUT ONLY and have NO internal pull-up/pull-down on the
// ESP32, so an unplugged sensor leaves this pin floating: it reads a
// noisy, semi-random value instead of a clean 0. That noise then gets
// mapped into a fake "moisture %" — which is exactly the bug you're seeing.
//
// Fix: add a real 10kOhm resistor from GPIO34 to GND on the breadboard.
//   - Sensor plugged in: its analog output actively drives the pin, easily
//     overpowering a 10k pull-down, so real readings are unaffected.
//   - Sensor unplugged: the pull-down holds the pin near 0V (rawMoisture
//     close to 0), which we can now reliably detect in software below.
#define SOIL_DRY_VALUE   4095   // raw ADC reading in dry air (calibrate for your sensor)
#define SOIL_WET_VALUE   1000   // raw ADC reading fully submerged (calibrate for your sensor)
#define SOIL_DISCONNECTED_THRESHOLD 50  // below this, treat as "no sensor" (with pull-down installed)

const int fanPin = 25;
const int pumpPin = 26;
const int lightPin = 27;

void setup() {
  // Disable brownout detector to prevent reset loops during Wi-Fi spikes
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  Serial.begin(115200);
  delay(2000); 
  Serial.println("\n--- Starting ESP32 ---");
  
  dht.begin();
  
  pinMode(fanPin, OUTPUT);
  pinMode(pumpPin, OUTPUT);
  pinMode(lightPin, OUTPUT);
  pinMode(SOIL_MOISTURE_PIN, INPUT); 
  
  digitalWrite(fanPin, LOW);
  digitalWrite(pumpPin, LOW);
  digitalWrite(lightPin, LOW);

  Serial.print("Connecting to Wi-Fi ");
  WiFi.begin(ssid, password);
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Connected!");
}

void loop() {
  // --- Read DHT11 Sensor ---
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  bool dhtOk = true;
  
  if (isnan(temp) || isnan(hum)) {
    Serial.println("DHT11 Error: Sensor disconnected or wired wrong!");
    temp = 0.0;
    hum = 0.0;
    dhtOk = false;
  } else {
    Serial.print("Temp: ");
    Serial.print(temp);
    Serial.print("C, Humidity: ");
    Serial.print(hum);
    Serial.println("%");
  }
  
  // --- Read Soil Moisture Sensor ---
  int rawMoisture = analogRead(SOIL_MOISTURE_PIN);
  int soilMoisture;
  bool soilOk;

  if (rawMoisture < SOIL_DISCONNECTED_THRESHOLD) {
    // Pull-down resistor holds this near 0 when nothing is plugged in —
    // report 0 directly instead of letting map() turn the noise into a
    // fake percentage.
    soilMoisture = 0;
    soilOk = false;
    Serial.println("Soil Moisture: sensor disconnected (raw near 0)");
  } else {
    soilMoisture = map(rawMoisture, SOIL_DRY_VALUE, SOIL_WET_VALUE, 0, 100);
    soilMoisture = constrain(soilMoisture, 0, 100);
    soilOk = true;
    Serial.print("Soil Moisture: ");
    Serial.print(soilMoisture);
    Serial.println("%");
  }

  // --- Device Status Variables ---
  String fanStatus = "OFF";
  String pumpStatus = "OFF";
  String lightStatus = "OFF";

  // --- Fan Logic ---
  if (temp >= 30.0) {
    digitalWrite(fanPin, HIGH);
    fanStatus = "ON";
  } else {
    digitalWrite(fanPin, LOW);
    fanStatus = "OFF";
  }
  
  // --- Pump Logic ---
  // Turns pump ON if moisture is below 30% (and the sensor is actually connected —
  // otherwise a disconnected sensor reading 0% would falsely trigger watering)
  if (soilOk && soilMoisture < 30) {
    digitalWrite(pumpPin, HIGH);
    pumpStatus = "ON";
  } else {
    digitalWrite(pumpPin, LOW);
    pumpStatus = "OFF";
  }

  // --- Send Data via HTTP POST ---
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<200> doc;
    doc["temperature"] = temp;
    doc["humidity"] = hum;
    doc["soil_moisture"] = soilMoisture;
    doc["soil_connected"] = soilOk;   // NEW: lets the dashboard show the real status
    doc["dht_connected"] = dhtOk;     // NEW: same idea for temp/humidity
    doc["fan"] = fanStatus;
    doc["water_pump"] = pumpStatus;
    doc["light"] = lightStatus;

    String requestBody;
    serializeJson(doc, requestBody);

    int httpResponseCode = http.POST(requestBody);
    Serial.print("HTTP POST Response: ");
    Serial.println(httpResponseCode);
    
    http.end();
  } else {
    Serial.println("Wi-Fi Connection Lost!");
  }
  
  Serial.println("-----------------------");
  delay(2000); 
}
