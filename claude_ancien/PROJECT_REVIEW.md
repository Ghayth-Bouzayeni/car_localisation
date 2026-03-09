# 🚗 Backend IoT Parking Solution - Project Review

## Executive Summary

This is a **complete backend system for managing 1000+ vehicles using BLE (Bluetooth Low Energy) tags**. It's built with Flask and PostgreSQL to track vehicle positions and manage alerts in a parking/distribution facility. The system provides real-time vehicle location tracking, automated alert management, and a modern web interface for visualization.

---

## Project Architecture

### System Flow

```
┌─────────────────┐
│  BLE Cloud      │
│  (Tag Data)     │
└────────┬────────┘
         │ POST /webhook
         │
┌────────▼────────────────┐
│   Backend (Flask)       │
│   + PostgreSQL          │
│  ├─ /api/vehicles       │
│  ├─ /api/positions      │
│  ├─ /api/alerts         │
│  └─ /webhook (receiver) │
└────────┬────────────────┘
         │ REST API
         │
┌────────▼────────────────┐
│  Frontend (Leaflet Map) │
│  ├─ Vehicle Map         │
│  ├─ Filters & Stats     │
│  └─ Real-time Updates   │
└─────────────────────────┘
```

---

## Project Components

### 1️⃣ Backend Server (`server.py`)

**Purpose**: REST API server for vehicle and position management

**Key Features**:

- Runs on `http://localhost:8000`
- CORS-enabled for cross-origin requests
- Integrates with PostgreSQL via SQLAlchemy ORM

**Main Endpoints**:

| Endpoint                  | Method | Purpose                                     |
| ------------------------- | ------ | ------------------------------------------- |
| `/api/vehicles`           | GET    | List all vehicles with pagination & filters |
| `/api/vehicles/<tag_id>`  | GET    | Get specific vehicle by BLE tag             |
| `/api/vehicles/associate` | POST   | Register/associate a BLE tag to a vehicle   |
| `/api/positions`          | GET    | Get vehicle positions with filters          |
| `/webhook`                | POST   | Receive location updates from BLE Cloud     |
| `/callback.html`          | GET    | Web form for tag-to-vehicle association     |
| `/debug/status`           | GET    | Debug endpoint for system status            |

**Query Parameters**:

- `zone`: Filter by parking zone
- `status`: Filter by vehicle status (parked/moved/alert)
- `fault_status`: Filter by fault condition
- `country`: Filter by delivery country
- `limit`: Results per page (default: 100)
- `offset`: Pagination offset

---

### 2️⃣ Data Models (`models.py`)

#### **Vehicle Table**

Stores core vehicle information:

```python
- id (PK)                    # Auto-increment ID
- vin                        # Vehicle ID Number (17 chars, unique)
- ble_tag_id                 # BLE tag identifier (unique)
- model, color               # Vehicle specs
- zone                       # Parking zone assignment
- delivery_date              # Delivery scheduled date
- expected_delivery_date     # Expected delivery date
- status                     # parked | moved | alert
- fault_status              # Boolean - missing parts, etc.
- customer                   # Customer name
- delivery_country           # Destination country
- association_date           # When tag was linked
- created_at, updated_at     # Timestamps
```

#### **Location Table**

GPS tracking history for each vehicle:

```python
- id (PK)
- ble_tag_id (FK)           # Links to vehicle
- latitude, longitude        # GPS coordinates (decimal precision)
- accuracy                   # GPS accuracy in meters
- movement_status           # static | moving
- battery_level             # BLE tag battery %
- received_at               # Timestamp
- is_latest                 # Flag for most recent position
```

#### **Alert Table**

Alerts and notifications:

```python
- id (PK)
- vehicle_id (FK)           # Links to vehicle
- alert_type               # unauthorized_move | parking_exceeded | etc.
- message                   # Detail message
- is_resolved              # Boolean resolution status
- created_at               # Timestamp
```

**Indexes for Performance**:

- `idx_vehicles_vin` - Fast VIN lookups
- `idx_vehicles_ble_tag` - Fast tag lookups
- `idx_locations_ble_tag_recency` - Latest positions
- `idx_alerts_vehicle` - Alert queries

---

### 3️⃣ Database Setup (`create_db.py`)

**Purpose**: Initialize PostgreSQL schema

**Features**:

- Connects to PostgreSQL using connection string from `.env`
- Creates all 3 tables with proper constraints
- Adds 5 performance indexes
- Includes CASCADE deletion for data integrity
- Provides success/error feedback

**Usage**:

```bash
python create_db.py
```

---

### 4️⃣ Frontend Map Interface (`index.html`)

**Purpose**: Interactive visualization of vehicle positions

**Features**:

- Uses Leaflet.js for mapping
- Real-time vehicle markers on map
- Statistics display (total vehicles, alerts, etc.)
- Filter controls:
  - By zone
  - By status (parked/moved/alert)
  - By fault status
- Responsive design with gradient header
- 600px height interactive map
- Modern UI with hover effects

**Color Coding**:

- Green markers: Parked vehicles
- Orange markers: Moving vehicles
- Red markers: Alerts

---

### 5️⃣ Vehicle Registration Form (`callback.html`)

**Purpose**: Web form to associate BLE tags with vehicles

**Flow**:

1. BLE Cloud sends user to: `callback.html?device_id=TAG_ID`
2. Form captures vehicle info:
   - Plate number
   - Make (brand)
   - Model
3. Data sent to backend via POST `/register-car`
4. Backend creates Vehicle record in database

**Form Fields**:

- Device ID (auto-extracted from URL)
- Plate number
- Make/Brand
- Model

---

### 6️⃣ Startup Script (`start.sh`)

**Purpose**: Automated setup and launch

**Workflow**:

1. Checks Python installation
2. Checks PostgreSQL availability
3. Installs Python dependencies from `requirements.txt`
4. Creates database schema via `create_db.py`
5. Launches Flask server on port 8000

**Output URLs**:

- Frontend Map: `http://localhost:8000/map`
- API: `http://localhost:8000/api/vehicles`
- Webhook: `http://localhost:8000/webhook`
- Callback: `http://localhost:8000/callback.html?device_id=YOUR_TAG`

---

### 7️⃣ Dependencies (`requirements.txt`)

| Package          | Version | Purpose               |
| ---------------- | ------- | --------------------- |
| Flask            | 3.0.0   | Web framework         |
| Flask-SQLAlchemy | 3.1.1   | ORM integration       |
| Flask-CORS       | 4.0.0   | Cross-origin support  |
| SQLAlchemy       | 2.0.23  | Database ORM          |
| psycopg2-binary  | 2.9.9   | PostgreSQL driver     |
| python-dotenv    | 1.0.0   | Environment variables |
| Werkzeug         | 3.0.0   | WSGI utilities        |

---

## Data Flow

### Registration Flow

```
1. BLE Cloud redirects user to /callback.html?device_id=XXX
2. User fills form with vehicle details
3. Form POSTs to /register-car
4. Backend creates Vehicle record in DB
5. Success message displayed
```

### Position Tracking Flow

```
1. BLE Cloud POSTs location to /webhook
   {ble_tag_id, latitude, longitude, accuracy, battery_level, movement_status}
2. Backend creates Location record
3. Updates is_latest flag
4. Triggers alerts if needed (e.g., unauthorized movement)
5. Frontend polls /api/positions and updates map
```

### Alert Generation

```
1. Unauthorized movement detected
2. Alert record created with type and message
3. is_resolved = false initially
4. Frontend displays alert notification
5. Admin marks as resolved via API
```

---

## Configuration

### Environment Variables (`.env`)

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/iot_parking
```

**Requirements**:

- PostgreSQL server running
- Database `iot_parking` created
- User with proper permissions

---

## Technology Stack

| Layer        | Technology              |
| ------------ | ----------------------- |
| **Backend**  | Python 3.9+, Flask 3.0  |
| **Database** | PostgreSQL 12+          |
| **ORM**      | SQLAlchemy 2.0          |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Mapping**  | Leaflet.js              |
| **API**      | RESTful JSON            |

---

## Features & Capabilities

### ✅ Implemented Features

- ✓ BLE tag registration and management
- ✓ Real-time GPS position tracking
- ✓ Alert system for unauthorized movements
- ✓ Vehicle filtering (zone, status, country, fault)
- ✓ Interactive map visualization
- ✓ Pagination support (limit/offset)
- ✓ Latest position caching
- ✓ Battery level monitoring
- ✓ Movement status detection (static/moving)
- ✓ CORS-enabled API
- ✓ Automatic schema creation
- ✓ Data integrity with CASCADE deletes

### 🔄 Supported Statuses

- **Vehicle Status**: parked, moved, alert
- **Movement Status**: static, moving
- **Alert Types**: unauthorized_move, parking_exceeded, etc.
- **Fault Status**: Boolean (true/false)

---

## Performance Considerations

### Database Optimization

- **Indexes on high-query columns**: VIN, BLE tag, location recency
- **Composite index**: location queries by tag + timestamp
- **Latest position flag**: Avoids scanning all historical positions
- **Foreign key constraints**: Maintains referential integrity
- **CASCADE deletes**: Automatically removes related records

### API Optimization

- Pagination support (limit/offset)
- Filter before returning results
- Latest position marked in DB
- Efficient ORM queries with filters

---

## Security Notes

### ⚠️ Current Implementation

- Basic CORS enabled (check origin restrictions)
- No authentication/authorization on API endpoints
- Environment variables store DB credentials

### 🔒 Recommendations

- Add JWT or API key authentication
- Implement rate limiting
- Validate all input data
- Add HTTPS in production
- Use secured PostgreSQL connection
- Add request validation/sanitization
- Implement role-based access control (RBAC)

---

## Deployment Checklist

- [ ] Python 3.9+ installed
- [ ] PostgreSQL 12+ running
- [ ] Create `.env` file with `DATABASE_URL`
- [ ] Run `pip install -r requirements.txt`
- [ ] Run `python create_db.py`
- [ ] Run `python server.py` or `./start.sh`
- [ ] Verify API at `http://localhost:8000/api/vehicles`
- [ ] Access map at `http://localhost:8000/`

---

## Future Enhancement Opportunities

1. **Authentication**: Add JWT token authentication
2. **Real-time Updates**: WebSocket support for live tracking
3. **Advanced Analytics**: Vehicle movement patterns, predictions
4. **Mobile App**: Native mobile client
5. **Multi-tenant**: Support multiple parking facilities
6. **Geofencing**: Define and monitor parking zones
7. **Email Alerts**: Send notifications on alerts
8. **Dashboard**: Admin dashboard for management
9. **Export**: CSV/PDF reports
10. **Caching**: Redis for session/data caching

---

## Summary

This is a **production-ready prototype** for a comprehensive **BLE-based vehicle fleet tracking system**. The architecture is scalable to 1000+ vehicles with proper indexing and can be extended with additional features like real-time WebSockets, advanced authentication, and analytics.

**Best suited for**:

- Auto distribution centers
- Parking facility management
- Vehicle inventory tracking
- Fleet vehicle monitoring
- Vehicle delivery systems

---

_Last Updated: February 27, 2026_
