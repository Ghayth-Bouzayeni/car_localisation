from fastapi import FastAPI, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models import Base, Vehicle, Location, Device, VehicleDeviceAssociation
from database import SessionLocal, engine
from schemas import VehicleCreate, VehicleUpdate, VehicleOut, LocationOut, VehicleFrontOut
import uvicorn
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware


# Créer les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BLEkon API")


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
                    raw_id = str(event["data"]["device_id"]).lower()
                    base_id = raw_id.removeprefix("urn:uuid:")
                    candidates = {raw_id, base_id}
                    if len(base_id) == 32:  # also try dashed UUID form
                        dashed = f"{base_id[0:8]}-{base_id[8:12]}-{base_id[12:16]}-{base_id[16:20]}-{base_id[20:32]}"
                        candidates.add(dashed)

                    coords = event["data"]["geojson"]["geometry"]["coordinates"]  # [lon, lat]
                    accuracy = event["data"]["quality"].get("accuracy_meters")
                    movement_status = event["data"].get("movement_status", "static")

                    device = db.query(Device).filter(Device.device_identifier.in_(list(candidates))).first()
                    if not device:
                        continue

                    association = db.query(VehicleDeviceAssociation).filter(
                        VehicleDeviceAssociation.device_id == device.id,
                        VehicleDeviceAssociation.active == True
                    ).first()
                    if not association:
                        continue

                    vehicle = db.query(Vehicle).filter(Vehicle.id == association.vehicle_id).first()
                    if not vehicle:
                        continue

                    location = Location(
                        device_id=device.id,
                        latitude=coords[1],
                        longitude=coords[0],
                        accuracy=accuracy,
                        movement_status=movement_status,
                        received_at=datetime.utcnow()
                    )
                    db.add(location)
                    db.commit()

        # Case 2: vendor tag batch (fields: tag_id, vendor, last_lat, last_lon, is_moving, updated_at)
        elif data and isinstance(data[0], dict) and "tag_id" in data[0]:
            for tag in data:
                raw_id = str(tag.get("tag_id", "")).lower()
                if not raw_id:
                    continue

                base_id = raw_id.removeprefix("urn:uuid:")
                candidates = {raw_id, base_id}
                if len(base_id) == 32:
                    dashed = f"{base_id[0:8]}-{base_id[8:12]}-{base_id[12:16]}-{base_id[16:20]}-{base_id[20:32]}"
                    candidates.add(dashed)

                lat = tag.get("last_lat")
                lon = tag.get("last_lon")
                if lat is None or lon is None:
                    continue

                movement_status = "moving" if tag.get("is_moving") else "static"

                ts = tag.get("updated_at") or tag.get("last_seen")
                received_at = datetime.utcnow()
                if isinstance(ts, str):
                    try:
                        received_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        received_at = datetime.utcnow()

                device = db.query(Device).filter(Device.device_identifier.in_(list(candidates))).first()
                if not device:
                    continue

                association = db.query(VehicleDeviceAssociation).filter(
                    VehicleDeviceAssociation.device_id == device.id,
                    VehicleDeviceAssociation.active == True
                ).first()
                if not association:
                    continue

                vehicle = db.query(Vehicle).filter(Vehicle.id == association.vehicle_id).first()
                if not vehicle:
                    continue

                location = Location(
                    device_id=device.id,
                    latitude=lat,
                    longitude=lon,
                    accuracy=None,
                    movement_status=movement_status,
                    received_at=received_at
                )
                db.add(location)
                db.commit()

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