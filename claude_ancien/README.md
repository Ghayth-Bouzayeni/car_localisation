# 🚗 Backend IoT Parking Solution

Architecture backend complète pour la gestion de 1000+ véhicules avec tags BLE.

## Architecture Système

```
┌─────────────────┐
│  BLEcon Cloud   │
│   (Tag BLE)     │
└────────┬────────┘
         │ POST /webhook
         │
┌────────▼────────────────┐
│   Backend Flask + PostgreSQL │
│  ├─ /api/vehicles       │
│  ├─ /api/positions      │
│  ├─ /api/alerts         │
│  └─ /webhook (reçoit)   │
└────────┬────────────────┘
         │ REST API
         │
┌────────▼────────────────┐
│  Frontend (autre app)   │
│  ├─ Carte (Leaflet)     │
│  ├─ Filtres             │
│  └─ Alertes             │
└─────────────────────────┘
```

## Installation

### 1. Prérequis

- Python 3.9+
- PostgreSQL 12+
- pip

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Créer la base de données PostgreSQL

```bash
# Créer la base
createdb iot_parking

# Ou via psql
psql
CREATE DATABASE iot_parking;
\q
```

### 4. Configurer le fichier .env

Modifiez `.env` avec vos infos PostgreSQL:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/iot_parking
```

### 5. Créer les tables

```bash
python create_db.py
```

### 6. Lancer le serveur

```bash
python server.py
```

Le serveur démarre sur `http://localhost:8000`

## Structure Base de Données

### Table: vehicles

Stocke les infos des véhicules

```sql
- id (PK)
- vin (VARCHAR 17, UNIQUE) - Numéro de châssis
- ble_tag_id (VARCHAR 50, UNIQUE) - ID du tag BLE
- model, color, zone
- delivery_date, expected_delivery_date
- status (parked/moved/alert)
- fault_status (booléen - pièce manquante, etc)
- customer, delivery_country
```

### Table: locations

Historique des positions reçues

```sql
- id (PK)
- ble_tag_id (FK -> vehicles)
- latitude, longitude (DECIMAL)
- accuracy (en mètres)
- movement_status (static/moving)
- battery_level (%)
- received_at (TIMESTAMP)
- is_latest (booléen - dernière position?)
```

### Table: alerts

Alertes sur les véhicules

```sql
- id (PK)
- vehicle_id (FK -> vehicles)
- alert_type (unauthorized_move, parking_exceeded, etc)
- message (TEXT)
- is_resolved (booléen)
- created_at
```

## Endpoints API

### 📍 Véhicules

**GET /api/vehicles** - Récupérer tous les véhicules avec filtres

```bash
GET /api/vehicles?zone=A1&status=parked&limit=50&offset=0
```

Réponse:

```json
{
  "total": 120,
  "limit": 50,
  "offset": 0,
  "vehicles": [
    {
      "id": 1,
      "vin": "WVWZZ3CZ5DE123456",
      "ble_tag_id": "urn:uuid:...",
      "model": "Golf GTI",
      "color": "Noir",
      "zone": "A1",
      "status": "parked",
      ...
    }
  ]
}
```

**GET /api/vehicles/<tag_id>** - Récupérer un véhicule

```bash
GET /api/vehicles/urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d
```

### 🔗 Association Véhicule/Tag BLE

**GET /callback.html?device_id=<tag_id>** - Page d'association
Affiche un formulaire si le tag n'existe pas

**POST /api/vehicles/associate** - Associer un tag à un véhicule

```bash
curl -X POST http://localhost:8000/api/vehicles/associate \
  -H "Content-Type: application/json" \
  -d '{
    "ble_tag_id": "urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d",
    "vin": "WVWZZ3CZ5DE123456",
    "model": "Golf GTI",
    "color": "Noir",
    "zone": "A1",
    "delivery_date": "2026-03-15",
    "customer": "Client XYZ",
    "delivery_country": "Morocco"
  }'
```

### 📍 Positions

**GET /api/positions** - Toutes les positions actuelles

```bash
GET /api/positions?zone=A1&status=parked&limit=100
```

**GET /api/positions/<tag_id>** - Historique d'un véhicule

```bash
GET /api/positions/urn:uuid:..?limit=50
```

Réponse JSON:

```json
{
  "ble_tag_id": "urn:uuid:...",
  "history": [
    {
      "id": 1,
      "latitude": 5.3654,
      "longitude": -3.9369,
      "accuracy": 45,
      "battery_level": 85,
      "movement_status": "static",
      "received_at": "2026-02-22T15:30:45.123Z",
      "is_latest": true
    }
  ]
}
```

### 🔔 Webhook BLE

**POST /webhook** - Recevoir les positions du cloud BLEcon
Format attendu (array d'événements):

```json
[
  {
    "type": "network.device_position",
    "data": {
      "device_id": "urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d",
      "geojson": {
        "geometry": {
          "coordinates": [-3.9369, 5.3671] // [longitude, latitude]
        }
      },
      "quality": {
        "accuracy_meters": 45
      },
      "battery_level": 85,
      "movement_status": "static"
    }
  }
]
```

**POST /test-webhook** - Tester le webhook

```bash
curl -X POST http://localhost:8000/test-webhook
```

### 🚨 Alertes

**GET /api/alerts** - Les alertes actives

```bash
GET /api/alerts?resolved=false&limit=50
```

**PATCH /api/alerts/<alert_id>/resolve** - Marquer resolved

```bash
curl -X PATCH http://localhost:8000/api/alerts/1/resolve
```

### 🔍 Debug

**GET /debug/status** - Statut global du système

```json
{
  "status": "running",
  "database": "connected",
  "vehicles": {
    "total": 250,
    "by_zone": [
      { "zone": "A1", "count": 50 },
      { "zone": "B1", "count": 75 }
    ]
  },
  "positions": {
    "total": 15000,
    "latest": 250
  },
  "alerts": {
    "total": 12,
    "unresolved": 3
  }
}
```

## Flux Complet d'Utilisation

### 1️⃣ Utilisateur scanne le QR code du tag BLE

- Vers: `http://localhost:8000/callback.html?device_id=URN_UUID`

### 2️⃣ Si tag n'existe pas → Formulaire d'association

- L'utilisateur remplit: VIN, Modèle, Couleur, Zone, etc.
- POST `/api/vehicles/associate`

### 3️⃣ Backend reçoit positions du cloud BLE

- POST `/webhook` (webhook du cloud BLE configuré)
- Les positions sont stockées en PostgreSQL avec timestamp

### 4️⃣ Frontend affiche la carte

- GET `/api/positions` pour les positions actuelles
- GET `/api/positions?zone=A1` pour filtrer par zone
- Mise à jour toutes les 5 secondes

### 5️⃣ Alertes générées automatiquement

- Mouvement non autorisé (si status=moved)
- Dépassement de parking
- Batterie faible
- Etc.

## Configuration du cloud BLE

Dans votre console BLEcon Cloud:

1. Allez à **Webhooks**
2. Ajoutez un webhook POST:
   - **URL**: `https://YOUR_NGROK_URL/webhook`
   - **Type**: POST
   - **Format**: JSON
   - **Trigger**: network.device_position

3. Testez l'envoi depuis la console

## Utilisation avec NGrok (pour production)

```bash
# Terminal 1: Lancer le serveur
python server.py

# Terminal 2: Exposer via ngrok
ngrok http 8000

# Copier l'URL ngrok
# https://xxx-xxxx-xxxx-xxxx.ngrok-free.app/webhook
```

Puis configurer cette URL dans le cloud BLE.

## Optimisations

### Indexes PostgreSQL

```sql
-- Déjà créés automatiquement
- idx_vehicles_bin
- idx_vehicles_ble_tag
- idx_locations_ble_tag_recency
- idx_locations_current
- idx_alerts_vehicle
```

### Pagination

Tous les endpoints supportent `limit` et `offset`:

```bash
GET /api/vehicles?limit=50&offset=100
```

### Filtres

- Zone: `?zone=A1`
- Status: `?status=parked`
- Pays: `?country=Morocco`
- Alertes résolues: `?resolved=true`

## Dépannage

### Erreur: "SQLALCHEMY_DATABASE_URI not set"

→ Vérifiez le fichier `.env`

### Erreur: "could not connect to server"

```bash
# Vérifier que PostgreSQL tourne
sudo systemctl status postgresql

# Ou sur Mac
brew services list
```

### Erreur: "permission denied" pour PostgreSQL

```bash
# Réinitialiser le mot de passe postgres
sudo -u postgres psql
\password postgres
```

### Webhook ne reçoit pas de positions

1. Vérifier ngrok est démarré
2. URL du webhook configurée dans cloud BLE
3. Vérifier les logs du backend
4. Tester avec `/test-webhook`

## Performance

Avec 1000+ véhicules:

- **GET /api/vehicles** → ~50ms (avec index)
- **POST /webhook** → ~100ms (insert + update)
- **GET /api/positions** → ~30ms

Pour améliorer:

- Ajouter Redis pour le cache
- Paginer toutes les queries
- Archiver les vieilles positions

## Prochaines Étapes

1. ✅ Base de données PostgreSQL
2. ✅ API complète
3. ✅ Webhook BLE
4. 🔄 Frontend (à faire par l'autre équipe)
5. 🔄 Authentification OAuth
6. 🔄 WebSockets pour temps réel
7. 🔄 Analytics/Dashboard
