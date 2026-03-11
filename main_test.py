from fastapi import FastAPI, Request
import uvicorn
from datetime import datetime

app = FastAPI(title="Webhook Test Server")

# Store received webhooks in memory
received_webhooks = []

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    timestamp = datetime.utcnow().isoformat()
    
    print(f"\n{'='*60}")
    print(f"📨 WEBHOOK RECEIVED at {timestamp}")
    print(f"{'='*60}")
    
    for event in data:
        event_type = event.get("type", "unknown")
        print(f"  Type: {event_type}")
        
        if event_type == "network.device_position":
            device_id = event["data"]["device_id"]
            coords = event["data"]["geojson"]["geometry"]["coordinates"]
            accuracy = event["data"]["quality"]["accuracy_meters"]
            movement = event["data"].get("movement_status", "unknown")
            
            print(f"  Device: {device_id}")
            print(f"  Lat: {coords[1]}, Lon: {coords[0]}")
            print(f"  Accuracy: {accuracy}m")
            print(f"  Movement: {movement}")
        else:
            print(f"  Raw data: {event}")
    
    received_webhooks.append({"timestamp": timestamp, "data": data})
    print(f"\n✅ Total webhooks received: {len(received_webhooks)}")
    
    return {"status": "ok"}

@app.get("/")
def home():
    return {
        "message": "Webhook test server running",
        "total_webhooks": len(received_webhooks),
        "webhooks": received_webhooks[-10:]  # last 10
    }

if __name__ == "__main__":
    print("🚀 Webhook test server starting on http://0.0.0.0:8000")
    print("📡 Expose with: ngrok http 8000")
    print("🔗 Then set BLEcon webhook to: https://your-ngrok-url/webhook")
    print("🌐 View received webhooks at: http://localhost:8000/")
    uvicorn.run("main_test:app", host="0.0.0.0", port=8000, reload=True)
