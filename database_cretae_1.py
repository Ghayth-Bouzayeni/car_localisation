"""
Script de création du schéma PostgreSQL pour ton projet BLE
Exécutez ce script avec: python create_db.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

print("=" * 50)
print("🚀 DÉBUT DE LA CRÉATION DE LA BASE DE DONNÉES")
print("=" * 50)

# URL de connexion à PostgreSQL
DATABASE_URL = "postgresql://postgres:9115gbz@localhost:5432/iot_ble"
print(f"📡 Connexion à: {DATABASE_URL.replace('9115gbz', '******')}")

# SQL pour créer les tables
SQL_SCHEMA = """
-- ==============================
-- 🔥 DROP EXISTING TABLES
-- ==============================

DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS vehicle_device_associations CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS devices CASCADE;

DROP TYPE IF EXISTS movement_enum CASCADE;
DROP TYPE IF EXISTS vehicle_status_enum CASCADE;

-- ==============================
-- 📌 ENUM TYPES
-- ==============================

CREATE TYPE movement_enum AS ENUM ('static', 'moving');

CREATE TYPE vehicle_status_enum AS ENUM (
    'parked',
    'in_transit',
    'delivered',
    'maintenance'
);

-- ==============================
-- 📌 DEVICES TABLE
-- ==============================

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_identifier VARCHAR(50) UNIQUE NOT NULL,
    battery_level INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- 📌 VEHICLES TABLE
-- ==============================

CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    vin VARCHAR(17) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL,
    color VARCHAR(50) NOT NULL,
    zone VARCHAR(50) NOT NULL,
    entry_date DATE NOT NULL,
    delivery_date DATE,
    customer VARCHAR(200),
    delivery_country VARCHAR(100),
    expected_delivery_date DATE,
    status vehicle_status_enum DEFAULT 'parked',
    fault_status BOOLEAN DEFAULT false,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- 📌 ASSOCIATION TABLE
-- ==============================

CREATE TABLE vehicle_device_associations (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    association_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disassociation_date TIMESTAMP,
    active BOOLEAN DEFAULT true
);

-- ==============================
-- 📌 LOCATIONS TABLE
-- ==============================

CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    latitude NUMERIC(10,8) NOT NULL,
    longitude NUMERIC(11,8) NOT NULL,
    accuracy NUMERIC(5,2),
    movement_status movement_enum DEFAULT 'static',
    battery_level INTEGER,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- 📌 ALERTS TABLE
-- ==============================

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================
-- 📌 INDEXES
-- ==============================

CREATE INDEX idx_vehicles_vin ON vehicles(vin);

CREATE INDEX idx_devices_identifier ON devices(device_identifier);

CREATE INDEX idx_locations_device_recency 
ON locations(device_id, received_at DESC);

CREATE INDEX idx_association_active 
ON vehicle_device_associations(vehicle_id)
WHERE active = true;

CREATE INDEX idx_alerts_vehicle 
ON alerts(vehicle_id);
"""

try:
    # Créer la connexion
    print("\n🔄 Tentative de connexion à PostgreSQL...")
    engine = create_engine(DATABASE_URL)
    
    # Tester la connexion
    with engine.connect() as conn:
        print("✅ Connexion réussie à PostgreSQL")
        
        # Vérifier les tables avant exécution
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables_avant = [row[0] for row in result]
        print(f"📊 Tables avant exécution: {tables_avant if tables_avant else 'Aucune table'}")
        
        # Exécuter le script SQL
        print("\n🔄 Exécution du script SQL...")
        conn.execute(text(SQL_SCHEMA))
        conn.commit()
        print("✅ Script SQL exécuté avec succès")
        
        # Vérifier les tables après exécution
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables_apres = [row[0] for row in result]
        print(f"\n📊 Tables après exécution: {tables_apres}")
        
        # Compter les tables
        print(f"✅ {len(tables_apres)} tables créées avec succès")
        
        # Vérifier les types ENUM
        result = conn.execute(text("""
            SELECT typname 
            FROM pg_type 
            WHERE typname IN ('movement_enum', 'vehicle_status_enum')
        """))
        enums = [row[0] for row in result]
        print(f"📊 Types ENUM créés: {enums}")
        
except Exception as e:
    print(f"\n❌ ERREUR: {e}")
    print("\nVérifiez que:")
    print("1. PostgreSQL est en cours d'exécution")
    print("2. La base de données 'iot_ble' existe")
    print("3. Le mot de passe est correct (9115gbz)")
    print("4. Aucun autre programme n'utilise la base")

print("\n" + "=" * 50)
print("🏁 FIN DU SCRIPT")
print("=" * 50)

# Pause pour voir les résultats
input("\nAppuyez sur Entrée pour quitter...")