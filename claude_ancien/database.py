"""
Script de création du schéma PostgreSQL pour ton projet BLE
Exécutez ce script avec: python create_db.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Charger les variables d'environnement (ex: mot de passe, URL DB)
load_dotenv()

# URL de connexion à PostgreSQL
# Exemple: 'postgresql://postgres:password@localhost:5432/iot_ble'
DATABASE_URL = 'postgresql://postgres:9115gbz@localhost:5432/iot_ble'
# SQL pour créer les tables
SQL_SCHEMA = """
-- Table principale des véhicules / devices
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,                     -- identifiant interne
    device_id VARCHAR(50) UNIQUE NOT NULL,    -- identifiant BLE unique
    vin VARCHAR(17) UNIQUE NOT NULL,          -- VIN véhicule
    model VARCHAR(100) NOT NULL,              -- Modèle
    color VARCHAR(50) NOT NULL,               -- Couleur
    fault_status BOOLEAN DEFAULT false,       -- Indique un problème
    message TEXT,                             -- Message d'alerte ou info
    zone VARCHAR(50) NOT NULL,                -- Zone ou emplacement
    entry_date DATE NOT NULL,                 -- Date d'entrée
    delivery_date DATE NOT NULL,              -- Date de livraison
    customer VARCHAR(200),                    -- Nom du client
    delivery_country VARCHAR(100),            -- Pays de livraison
    expected_delivery_date DATE,              -- Date de livraison prévue
    status VARCHAR(20) DEFAULT 'parked',      -- Statut actuel
    association_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des positions des BLE tags
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL REFERENCES vehicles(device_id) ON DELETE CASCADE,
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

-- Index pour optimisation
CREATE INDEX IF NOT EXISTS idx_vehicles_vin ON vehicles(vin);
CREATE INDEX IF NOT EXISTS idx_vehicles_device_id ON vehicles(device_id);
CREATE INDEX IF NOT EXISTS idx_locations_device_id_recency ON locations(device_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_locations_current ON locations(device_id) WHERE is_latest = true;
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