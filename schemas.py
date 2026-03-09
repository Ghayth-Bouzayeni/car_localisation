from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

# =========================
# VEHICLE
# =========================

class VehicleCreate(BaseModel):
    # ⚠️ ATTENTION: device_id est retiré car il n'existe pas dans la table vehicles
    # L'association se fait via l'endpoint /associate et la table vehicle_device_associations
    vin: str
    model: str
    color: str
    zone: str
    entry_date: date
    delivery_date: Optional[date] = None  # Rendre optionnel
    customer: Optional[str] = None
    delivery_country: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    fault_status: Optional[bool] = False
    message: Optional[str] = None
    status: Optional[str] = "parked"


class VehicleUpdate(BaseModel):
    # ⚠️ device_id retiré - les associations se gèrent via /associate
    model: Optional[str] = None
    color: Optional[str] = None
    zone: Optional[str] = None
    fault_status: Optional[bool] = None
    message: Optional[str] = None
    status: Optional[str] = None
    delivery_date: Optional[date] = None
    customer: Optional[str] = None
    delivery_country: Optional[str] = None
    expected_delivery_date: Optional[date] = None


class VehicleOut(BaseModel):
    id: int
    # ⚠️ device_id retiré - il n'existe pas dans la table vehicles
    vin: str
    model: str
    color: str
    zone: str
    status: str
    entry_date: date
    delivery_date: Optional[date] = None
    customer: Optional[str] = None
    delivery_country: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    fault_status: bool
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # ✅ moderne (remplace orm_mode)


# =========================
# DEVICE SCHEMAS (NOUVEAU)
# =========================

class DeviceCreate(BaseModel):
    device_identifier: str
    battery_level: Optional[int] = None
    status: Optional[str] = "active"


class DeviceOut(BaseModel):
    id: int
    device_identifier: str
    battery_level: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# ASSOCIATION SCHEMAS (NOUVEAU)
# =========================

class AssociationCreate(BaseModel):
    vehicle_id: int
    device_identifier: str


class AssociationOut(BaseModel):
    id: int
    vehicle_id: int
    device_id: int
    association_date: datetime
    disassociation_date: Optional[datetime] = None
    active: bool

    class Config:
        from_attributes = True


class VehicleWithDeviceOut(BaseModel):
    """Pour retourner un véhicule avec son device associé"""
    vehicle: VehicleOut
    device: Optional[DeviceOut] = None
    association_active: bool = False


# =========================
# LOCATION
# =========================

class LocationBase(BaseModel):
    device_id: int  # C'est l'ID de la table devices, pas l'identifiant string
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    movement_status: str
    battery_level: Optional[int] = None
    received_at: datetime


class LocationCreate(LocationBase):
    pass


class LocationOut(LocationBase):
    id: int

    class Config:
        from_attributes = True


# =========================
# Pour la compatibilité avec le frontend
# =========================

class VehicleFrontOut(BaseModel):
    """Format spécifique pour le frontend si besoin"""
    id: int
    vin: str
    model: str
    color: str
    zone: str
    status: str
    device_identifier: Optional[str] = None  # 🔹 Ceci vient de l'association, pas de la table vehicles
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    last_position_time: Optional[datetime] = None

    class Config:
        from_attributes = True