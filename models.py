from sqlalchemy import Column, Integer, String, Boolean, Date, DECIMAL, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# -------------------
# VEHICLES
# -------------------
class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)
    vin = Column(String(17), unique=True, nullable=False)
    model = Column(String(100), nullable=False)
    color = Column(String(50), nullable=False)
    zone = Column(String(50), nullable=False)
    entry_date = Column(Date, nullable=False)
    delivery_date = Column(Date)
    customer = Column(String(200))
    delivery_country = Column(String(100))
    expected_delivery_date = Column(Date)
    status = Column(String(20), default="parked")
    fault_status = Column(Boolean, default=False)
    message = Column(String)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    associations = relationship("VehicleDeviceAssociation", back_populates="vehicle", cascade="all, delete")
    alerts = relationship("Alert", back_populates="vehicle", cascade="all, delete")


# -------------------
# DEVICES
# -------------------
class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    device_identifier = Column(String(50), unique=True, nullable=False)
    battery_level = Column(Integer)
    status = Column(String(20), default="active")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    associations = relationship("VehicleDeviceAssociation", back_populates="device", cascade="all, delete")
    locations = relationship("Location", back_populates="device", cascade="all, delete")


# -------------------
# VEHICLE ↔ DEVICE ASSOCIATION
# -------------------
class VehicleDeviceAssociation(Base):
    __tablename__ = "vehicle_device_associations"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    association_date = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    disassociation_date = Column(TIMESTAMP)
    active = Column(Boolean, default=True)

    vehicle = relationship("Vehicle", back_populates="associations")
    device = relationship("Device", back_populates="associations")


# -------------------
# LOCATIONS
# -------------------
class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    accuracy = Column(DECIMAL(5, 2))
    movement_status = Column(String(10), default="static")
    battery_level = Column(Integer)
    received_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    device = relationship("Device", back_populates="locations")


# -------------------
# ALERTS
# -------------------
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"))
    alert_type = Column(String(50), nullable=False)
    message = Column(String, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    vehicle = relationship("Vehicle", back_populates="alerts")