# BLEkon API — Frontend Documentation

**Base URL:** `https://car-localisation.onrender.com`

---

## Vehicles

### Get all cars
```
GET /cars
```
```json
[
  {
    "id": 2,
    "vin": "1HGCM82633A004352",
    "model": "Honda Civic",
    "color": "Red",
    "zone": "Zone A",
    "status": "parked",
    "entry_date": "2026-03-01",
    "delivery_date": null,
    "customer": "John Doe",
    "delivery_country": "Tunisia",
    "expected_delivery_date": null,
    "fault_status": false,
    "message": null,
    "created_at": "2026-03-09T23:01:14",
    "updated_at": "2026-03-09T23:01:14"
  }
]
```

### Get one car
```
GET /cars/{id}
```
Example: `GET /cars/2`

### Create a car
```
POST /cars
Content-Type: application/json

{
  "vin": "1HGCM82633A004352",
  "model": "Honda Civic",
  "color": "Red",
  "zone": "Zone A",
  "entry_date": "2026-03-01",
  "customer": "John Doe",               // optional
  "delivery_country": "Tunisia",        // optional
  "delivery_date": "2026-03-15",        // optional
  "expected_delivery_date": "2026-03-15", // optional
  "fault_status": false,                // optional
  "message": null,                      // optional
  "status": "parked"                    // optional
}
```

### Update a car
```
PUT /cars/{id}
Content-Type: application/json

{
  "status": "in_transit",       // optional — any field
  "fault_status": true,
  "message": "Engine issue"
}
```

### Delete a car
```
DELETE /cars/{id}
```

---

## Devices & Association

### Associate a device to a car
```
POST /associate?vehicle_id=2&device_identifier=ff69bfef-e2dd-4efb-bab3-d1b75408a7a3
```
```json
{
  "vehicle_id": 2,
  "device_id": "ff69bfef-e2dd-4efb-bab3-d1b75408a7a3",
  "association_active": true,
  "message": "Association créée avec succès"
}
```

### Get device associated to a car
```
GET /vehicles/{id}/device
```
Example: `GET /vehicles/2/device`
```json
{
  "vehicle_id": 2,
  "device_id": "ff69bfef-e2dd-4efb-bab3-d1b75408a7a3",
  "association_date": "2026-03-10T00:15:00"
}
```

---

## Positions

### 🗺️ Cars with positions — FOR THE MAP
> Returns only cars that have an active device association, with their latest GPS position.
```
GET /cars/with-positions
```
```json
[
  {
    "id": 2,
    "vin": "1HGCM82633A004352",
    "model": "Honda Civic",
    "color": "Red",
    "zone": "Zone A",
    "status": "parked",
    "device_identifier": "ff69bfef-e2dd-4efb-bab3-d1b75408a7a3",
    "last_latitude": 36.839016,
    "last_longitude": 10.193521,
    "last_position_time": "2026-03-10T00:00:53"
  }
]
```

### Latest position(s)
```
GET /positions/latest              → latest position of ALL vehicles
GET /positions/latest?car_id=2    → latest position of one vehicle
```

### Position history
```
GET /positions/history?car_id=2
GET /positions/history?car_id=2&start_date=2026-03-01T00:00:00&end_date=2026-03-10T23:59:59
```

---

## Webhook (BLEcon → API)
```
POST /webhook
```
> This is called automatically by BLEcon. Do not call this from the frontend.

---

## Interactive Docs
Full Swagger UI: `https://car-localisation.onrender.com/docs`
