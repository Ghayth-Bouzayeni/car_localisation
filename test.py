import requests
import json

url = " https://72b8-102-152-14-201.ngrok-free.app/cars"  # ton endpoint FastAPI/Flask
data = {
    "device_id": "urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d",
    "vin": "1HGCM82633A004352",
    "model": "Toyota Corolla",
    "color": "Red",
    "zone": "Zone A",
    "entry_date": "2026-03-01",
    "delivery_date": "2026-03-10",
    "customer": "John Doe",
    "delivery_country": "Tunisia",
    "expected_delivery_date": "2026-03-12",
    "fault_status": False,
    "message": "No issues",
    "status": "parked"
}

response = requests.post(url, json=data)
print(response.status_code)
print(response.json())