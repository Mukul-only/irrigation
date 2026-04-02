"""
Quick integration test — sends a sample payload to the live API.
Run after the server is started:
    python test_api.py
"""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"

payload = {
    "sensor": {
        "moisture_percent": 18,
        "soil_status": "Dry — needs water",
        "rain_percent": 0,
        "rain_status": "No rain",
        "temp_celsius": 24.5,
        "humidity_percent": 62,
        "tank_status": "OK",
        "tank_fill_percent": 74
    },
    "weather": {
        "temp_current": 23.1,
        "humidity_current": 58,
        "precipitation_now": 0,
        "wind_speed": 12.4,
        "description": "Clear sky",
        "rain_probability_next_6h": 5,
        "temp_next_6h": [24.1, 25.0, 26.3, 25.8, 24.5, 23.0]
    },
    "context": {
        "last_pump_command": "OFF",
        "last_pump_command_at": "2026-03-26T08:00:00Z",
        "moisture_threshold": 30
    }
}


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.loads(resp.read())


if __name__ == "__main__":
    print("=" * 60)
    print("1. Health check")
    print(json.dumps(get("/health"), indent=2))

    print("\n2. POST /api/v1/irrigate")
    result = post("/api/v1/irrigate", payload)
    print(json.dumps(result, indent=2, default=str))

    print("\n3. GET /api/v1/history")
    history = get("/api/v1/history?limit=5")
    print(json.dumps(history, indent=2, default=str))

    print("\n4. GET /api/v1/anomalies")
    anomalies = get("/api/v1/anomalies?limit=5")
    print(json.dumps(anomalies, indent=2, default=str))

    print("\n5. GET /api/v1/predictions")
    preds = get("/api/v1/predictions?limit=3")
    print(json.dumps(preds, indent=2, default=str))
