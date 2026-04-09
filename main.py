from fastapi import FastAPI, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models import Base, Vehicle, Location, Device, VehicleDeviceAssociation
from database import SessionLocal, engine
from schemas import VehicleCreate, VehicleUpdate, VehicleOut, LocationOut, VehicleFrontOut
import uvicorn
from datetime import datetime, timezone
import os
import json
import logging
import paho.mqtt.client as mqtt

from fastapi.middleware.cors import CORSMiddleware


# Créer les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BLEkon API")
logger = logging.getLogger("blekon_api")

MQTT_ENABLED = os.getenv("MQTT_ENABLED", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "parking/+/+/observations")

mqtt_client: mqtt.Client | None = None


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, mettez votre domaine spécifique
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------
# Dépendance pour DB session
# -------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_device_candidates(identifier: str) -> list[str]:
    raw_id = str(identifier or "").strip().lower()
    if not raw_id:
        return []

    base_id = raw_id.removeprefix("urn:uuid:")
    candidates = {raw_id, base_id}

    # Include prefixed variants to support historical values in DB.
    if base_id:
        candidates.add(f"urn:uuid:{base_id}")

    # If UUID arrives without dashes, also try dashed representation.
    if len(base_id) == 32:
        dashed = f"{base_id[0:8]}-{base_id[8:12]}-{base_id[12:16]}-{base_id[16:20]}-{base_id[20:32]}"
        candidates.add(dashed)
        candidates.add(f"urn:uuid:{dashed}")

    return [item for item in candidates if item]


def parse_received_at(ts: str | None) -> datetime:
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            pass
    return datetime.utcnow()


def save_location_for_identifier(
    db: Session,
    identifier: str,
    latitude: float,
    longitude: float,
    accuracy: float | None,
    movement_status: str,
    received_at: datetime,
) -> bool:
    candidates = build_device_candidates(identifier)
    if not candidates:
        return False

    device = db.query(Device).filter(Device.device_identifier.in_(candidates)).first()
    if not device:
        return False

    association = db.query(VehicleDeviceAssociation).filter(
        VehicleDeviceAssociation.device_id == device.id,
        VehicleDeviceAssociation.active == True
    ).first()
    if not association:
        return False

    vehicle = db.query(Vehicle).filter(Vehicle.id == association.vehicle_id).first()
    if not vehicle:
        return False

    location = Location(
        device_id=device.id,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        movement_status=movement_status,
        received_at=received_at,
    )
    db.add(location)
    db.commit()
    return True


def process_mqtt_observation(message: dict):
    ble_scan = message.get("ble_scan") or {}
    devices = ble_scan.get("devices") or []
    fallback_ts = message.get("timestamp")

    if not isinstance(devices, list):
        return

    db = SessionLocal()
    try:
        for dev in devices:
            if not isinstance(dev, dict):
                continue

            tag_id = dev.get("tag_id")
            lat = dev.get("latitude")
            lon = dev.get("longitude")
            if not tag_id or lat is None or lon is None:
                continue

            movement_status = "moving" if dev.get("is_moving") else "static"
            received_at = parse_received_at(dev.get("last_seen") or fallback_ts)
            accuracy = dev.get("accuracy")

            save_location_for_identifier(
                db=db,
                identifier=tag_id,
                latitude=lat,
                longitude=lon,
                accuracy=accuracy,
                movement_status=movement_status,
                received_at=received_at,
            )
    finally:
        db.close()


def on_mqtt_connect(client, userdata, flags, rc, *args):
    if rc == 0:
        logger.info("MQTT connected, subscribing to %s", MQTT_TOPIC)
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error("MQTT connection failed with rc=%s", rc)


def on_mqtt_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as exc:
        logger.error("MQTT payload decode error: %s", exc)
        return

    if isinstance(payload, dict):
        process_mqtt_observation(payload)


@app.on_event("startup")
def start_mqtt_subscriber():
    global mqtt_client

    if not MQTT_ENABLED:
        logger.info("MQTT subscriber disabled (MQTT_ENABLED=false)")
        return

    if not all([MQTT_HOST, MQTT_USER, MQTT_PASS, MQTT_TOPIC]):
        logger.warning("MQTT subscriber not started: missing MQTT_* env vars")
        return

    try:
        mqtt_client = mqtt.Client(client_id=f"blekon-api-{os.getpid()}")
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
        mqtt_client.tls_set()
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        logger.info("MQTT subscriber started")
    except Exception as exc:
        logger.error("Failed to start MQTT subscriber: %s", exc)


@app.on_event("shutdown")
def stop_mqtt_subscriber():
    global mqtt_client

    if mqtt_client is None:
        return

    try:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("MQTT subscriber stopped")
    except Exception as exc:
        logger.error("Failed to stop MQTT subscriber: %s", exc)

# -------------------
# Webhook pour positions
# -------------------
@app.post("/webhook")
async def blekon_webhook(request: Request):
    data = await request.json()
    db: Session = next(get_db())

    # Support both BLEcon native events (type=network.device_position) and vendor tag batches
    # New vendor payload example is a list of objects with fields like tag_id, vendor, last_lat/last_lon
    # We keep the same logic: only store if device exists and is actively associated to a vehicle.
    if isinstance(data, list):
        # Case 1: legacy BLEcon events with "type"
        if data and isinstance(data[0], dict) and "type" in data[0]:
            for event in data:
                if event.get("type") == "network.device_position":
                    coords = event["data"]["geojson"]["geometry"]["coordinates"]  # [lon, lat]
                    accuracy = (event.get("data", {}).get("quality") or {}).get("accuracy_meters")
                    movement_status = event["data"].get("movement_status", "static")
                    save_location_for_identifier(
                        db=db,
                        identifier=event["data"].get("device_id", ""),
                        latitude=coords[1],
                        longitude=coords[0],
                        accuracy=accuracy,
                        movement_status=movement_status,
                        received_at=datetime.utcnow(),
                    )

        # Case 2: vendor tag batch (fields: tag_id, vendor, last_lat, last_lon, is_moving, updated_at)
        elif data and isinstance(data[0], dict) and "tag_id" in data[0]:
            for tag in data:
                lat = tag.get("last_lat")
                lon = tag.get("last_lon")
                movement_status = "moving" if tag.get("is_moving") else "static"
                if lat is None or lon is None:
                    continue

                save_location_for_identifier(
                    db=db,
                    identifier=tag.get("tag_id", ""),
                    latitude=lat,
                    longitude=lon,
                    accuracy=None,
                    movement_status=movement_status,
                    received_at=parse_received_at(tag.get("updated_at") or tag.get("last_seen")),
                )

    return {"status": "ok"}

# -------------------
# Gestion des voitures
# -------------------
@app.post("/cars", response_model=VehicleOut)
def create_car(car: VehicleCreate, db: Session = Depends(get_db)):
    db_car = Vehicle(**car.dict())
    db.add(db_car)
    db.commit()
    db.refresh(db_car)
    return db_car

@app.get("/cars", response_model=list[VehicleOut])
def get_cars(db: Session = Depends(get_db)):
    return db.query(Vehicle).all()

# -------------------
# Voitures associées avec positions (pour la carte)
# -------------------
@app.get("/cars/with-positions", response_model=list[VehicleFrontOut])
def get_cars_with_positions(db: Session = Depends(get_db)):
    # Get all active associations with their vehicle and device
    associations = db.query(VehicleDeviceAssociation).filter(
        VehicleDeviceAssociation.active == True
    ).all()

    results = []
    for assoc in associations:
        vehicle = db.query(Vehicle).filter(Vehicle.id == assoc.vehicle_id).first()
        device = db.query(Device).filter(Device.id == assoc.device_id).first()
        if not vehicle or not device:
            continue

        # Get latest position for this device
        location = db.query(Location).filter(
            Location.device_id == device.id
        ).order_by(desc(Location.received_at)).first()

        results.append(VehicleFrontOut(
            id=vehicle.id,
            vin=vehicle.vin,
            model=vehicle.model,
            color=vehicle.color,
            zone=vehicle.zone,
            status=vehicle.status,
            device_identifier=device.device_identifier,
            association_date=assoc.association_date,
            last_latitude=float(location.latitude) if location else None,
            last_longitude=float(location.longitude) if location else None,
            last_position_time=location.received_at if location else None,
        ))

    return results

# -------------------
# Get all associated vehicles with their active device associations
# -------------------
@app.get("/vehicles/associated", response_model=list[VehicleFrontOut])
def get_associated_vehicles(include_positions: bool = Query(True), db: Session = Depends(get_db)):
    """Get all vehicles with active device associations.
    
    Args:
        include_positions: If True, includes latest position for each vehicle. Default: True
    
    Returns:
        List of vehicles with device_identifier and optionally latest position coordinates.
    """
    associations = db.query(VehicleDeviceAssociation).filter(
        VehicleDeviceAssociation.active == True
    ).all()

    results = []
    for assoc in associations:
        vehicle = db.query(Vehicle).filter(Vehicle.id == assoc.vehicle_id).first()
        device = db.query(Device).filter(Device.id == assoc.device_id).first()
        if not vehicle or not device:
            continue

        location = None
        if include_positions:
            location = db.query(Location).filter(
                Location.device_id == device.id
            ).order_by(desc(Location.received_at)).first()

        results.append(VehicleFrontOut(
            id=vehicle.id,
            vin=vehicle.vin,
            model=vehicle.model,
            color=vehicle.color,
            zone=vehicle.zone,
            status=vehicle.status,
            device_identifier=device.device_identifier,
            association_date=assoc.association_date,
            last_latitude=float(location.latitude) if location else None,
            last_longitude=float(location.longitude) if location else None,
            last_position_time=location.received_at if location else None,
        ))

    return results

@app.get("/cars/{car_id}", response_model=VehicleOut)
def get_car(car_id: int, db: Session = Depends(get_db)):
    car = db.query(Vehicle).filter(Vehicle.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return car

@app.put("/cars/{car_id}", response_model=VehicleOut)
def update_car(car_id: int, car_update: VehicleUpdate, db: Session = Depends(get_db)):
    car = db.query(Vehicle).filter(Vehicle.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    update_data = car_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(car, key, value)
    
    db.commit()
    db.refresh(car)
    return car

@app.delete("/cars/{car_id}")
def delete_car(car_id: int, db: Session = Depends(get_db)):
    car = db.query(Vehicle).filter(Vehicle.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    db.delete(car)
    db.commit()
    return {"message": "Vehicle deleted successfully"}

# -------------------
# Association voiture ↔ device
# -------------------
@app.post("/associate")
def associate_vehicle_device(vehicle_id: int, device_identifier: str, db: Session = Depends(get_db)):
    raw_device_id = device_identifier.lower()
    base_id = raw_device_id.removeprefix("urn:uuid:")
    candidates = {raw_device_id, base_id}
    if len(base_id) == 32:
        dashed = f"{base_id[0:8]}-{base_id[8:12]}-{base_id[12:16]}-{base_id[16:20]}-{base_id[20:32]}"
        candidates.add(dashed)
        canonical = dashed  # store dashed form without prefix
    else:
        canonical = base_id  # store prefixless form

    # 1️⃣ Vérifier si la voiture existe
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # 2️⃣ Vérifier si le device existe, sinon le créer (en stockant sans préfixe)
    device = db.query(Device).filter(Device.device_identifier.in_(list(candidates))).first()
    if not device:
        device = Device(device_identifier=canonical)
        db.add(device)
        db.commit()
        db.refresh(device)

    # 3️⃣ Désactiver les anciennes associations pour ce device
    db.query(VehicleDeviceAssociation).filter(
        VehicleDeviceAssociation.device_id == device.id,
        VehicleDeviceAssociation.active == True
    ).update({
        "active": False,
        "disassociation_date": datetime.utcnow()
    })

    # 4️⃣ Créer la nouvelle association
    new_association = VehicleDeviceAssociation(
        vehicle_id=vehicle.id,
        device_id=device.id,
        active=True,
        association_date=datetime.utcnow()
    )
    db.add(new_association)
    db.commit()

    return {
        "vehicle_id": vehicle.id,
        "device_id": device.device_identifier,
        "association_active": True,
        "message": "Association créée avec succès"
    }

# -------------------
# Obtenir le device associé à un véhicule
# -------------------
@app.get("/vehicles/{vehicle_id}/device")
def get_vehicle_device(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    association = db.query(VehicleDeviceAssociation).filter(
        VehicleDeviceAssociation.vehicle_id == vehicle_id,
        VehicleDeviceAssociation.active == True
    ).first()
    
    if not association:
        return {"vehicle_id": vehicle_id, "device_id": None, "message": "Aucun device associé"}
    
    device = db.query(Device).filter(Device.id == association.device_id).first()
    return {
        "vehicle_id": vehicle_id,
        "device_id": device.device_identifier if device else None,
        "association_date": association.association_date
    }

# -------------------
# Positions des voitures
# -------------------
@app.get("/positions/latest", response_model=list[LocationOut])
def get_latest_positions(car_id: int = Query(None), db: Session = Depends(get_db)):
    
    if car_id:
        # Cas 1: Position d'un véhicule spécifique
        vehicle = db.query(Vehicle).filter(Vehicle.id == car_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        # Récupérer l'association active
        association = db.query(VehicleDeviceAssociation).filter(
            VehicleDeviceAssociation.vehicle_id == car_id,
            VehicleDeviceAssociation.active == True
        ).first()
        
        if not association:
            return []  # Pas de device associé
        
        # Récupérer la dernière position du device
        location = db.query(Location).filter(
            Location.device_id == association.device_id
        ).order_by(desc(Location.received_at)).first()
        
        return [location] if location else []
    
    else:
        # Cas 2: Dernières positions de tous les véhicules
        # Sous-requête pour obtenir la dernière position de chaque device
        subquery = db.query(
            Location.device_id,
            func.max(Location.received_at).label("last_received")
        ).group_by(Location.device_id).subquery()
        
        # Jointure pour obtenir les positions complètes
        query = db.query(Location).join(
            subquery,
            (Location.device_id == subquery.c.device_id) &
            (Location.received_at == subquery.c.last_received)
        )
        
        return query.all()

@app.get("/positions/history", response_model=list[LocationOut])
def get_positions_history(
    car_id: int = Query(...),  # Requis pour l'historique
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: Session = Depends(get_db)
):
    # Vérifier si le véhicule existe
    vehicle = db.query(Vehicle).filter(Vehicle.id == car_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Récupérer toutes les associations de ce véhicule
    associations = db.query(VehicleDeviceAssociation).filter(
        VehicleDeviceAssociation.vehicle_id == car_id
    ).all()
    
    device_ids = [assoc.device_id for assoc in associations]
    
    if not device_ids:
        return []  # Aucun device associé
    
    # Construire la requête pour les positions
    query = db.query(Location).filter(Location.device_id.in_(device_ids))
    
    if start_date:
        query = query.filter(Location.received_at >= start_date)
    if end_date:
        query = query.filter(Location.received_at <= end_date)
    
    return query.order_by(desc(Location.received_at)).all()

# -------------------
# Lancer le serveur
# -------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)