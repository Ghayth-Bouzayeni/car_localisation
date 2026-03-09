"""
Script de création du schéma PostgreSQL
Exécutez ce script avec: python create_db.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/iot_parking')

# SQL pour créer les tables
SQL_SCHEMA = """
-- Table principale des véhicules
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    vin VARCHAR(17) UNIQUE NOT NULL,
    ble_tag_id VARCHAR(50) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    color VARCHAR(50) NOT NULL,
    fault_status BOOLEAN DEFAULT false,
    zone VARCHAR(50) NOT NULL,
    delivery_date DATE NOT NULL,
    customer VARCHAR(200),
    delivery_country VARCHAR(100),
    expected_delivery_date DATE,
    status VARCHAR(20) DEFAULT 'parked',
    association_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des positions reçues de Blecon
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    ble_tag_id VARCHAR(50) NOT NULL REFERENCES vehicles(ble_tag_id) ON DELETE CASCADE,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    accuracy DECIMAL(5, 2),
    movement_status VARCHAR(10) DEFAULT 'static',
    battery_level INTEGER,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_latest BOOLEAN DEFAULT false
);

-- Table des alertes
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_vehicles_vin ON vehicles(vin);
CREATE INDEX IF NOT EXISTS idx_vehicles_ble_tag ON vehicles(ble_tag_id);
CREATE INDEX IF NOT EXISTS idx_locations_ble_tag_recency ON locations(ble_tag_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_locations_current ON locations(ble_tag_id) WHERE is_latest = true;
CREATE INDEX IF NOT EXISTS idx_alerts_vehicle ON alerts(vehicle_id);
"""

if __name__ == '__main__':
    try:
        print("🔌 Connexion à PostgreSQL...")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("📊 Création du schéma PostgreSQL...")
            for statement in SQL_SCHEMA.split(';'):
                if statement.strip():
                    connection.execute(text(statement))
            connection.commit()
            print("✅ Schéma créé avec succès!")
            
        print("\n📋 Tables créées:")
        print("  - vehicles")
        print("  - locations")
        print("  - alerts")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        exit(1)
