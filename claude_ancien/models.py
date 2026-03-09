"""
Modèles SQLAlchemy pour la gestion des véhicules et positions BLE
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Vehicle(db.Model):
    """Modèle pour les véhicules"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), unique=True, nullable=False, index=True)
    ble_tag_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    fault_status = db.Column(db.Boolean, default=False)
    zone = db.Column(db.String(50), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    customer = db.Column(db.String(200))
    delivery_country = db.Column(db.String(100))
    expected_delivery_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='parked')  # parked, moved, alert
    association_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    locations = db.relationship('Location', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convertir en dictionnaire"""
        return {
            'id': self.id,
            'vin': self.vin,
            'ble_tag_id': self.ble_tag_id,
            'model': self.model,
            'color': self.color,
            'fault_status': self.fault_status,
            'zone': self.zone,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'customer': self.customer,
            'delivery_country': self.delivery_country,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'status': self.status,
            'association_date': self.association_date.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Vehicle {self.vin}>'


class Location(db.Model):
    """Modèle pour les positions BLE"""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    ble_tag_id = db.Column(db.String(50), db.ForeignKey('vehicles.ble_tag_id', ondelete='CASCADE'), nullable=False, index=True)
    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)
    accuracy = db.Column(db.Numeric(5, 2))  # Précision en mètres
    movement_status = db.Column(db.String(10), default='static')  # moving/static
    battery_level = db.Column(db.Integer)  # Niveau batterie du tag
    received_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_latest = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """Convertir en dictionnaire"""
        return {
            'id': self.id,
            'ble_tag_id': self.ble_tag_id,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'accuracy': float(self.accuracy) if self.accuracy else None,
            'movement_status': self.movement_status,
            'battery_level': self.battery_level,
            'received_at': self.received_at.isoformat(),
            'is_latest': self.is_latest
        }
    
    def __repr__(self):
        return f'<Location {self.ble_tag_id}>'


class Alert(db.Model):
    """Modèle pour les alertes"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False, index=True)
    alert_type = db.Column(db.String(50), nullable=False)  # unauthorized_move, parking_exceeded, etc.
    message = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convertir en dictionnaire"""
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'alert_type': self.alert_type,
            'message': self.message,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Alert {self.alert_type}>'
