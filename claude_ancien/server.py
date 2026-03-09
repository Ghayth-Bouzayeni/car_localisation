"""
Backend IoT Parking Solution avec PostgreSQL
API REST pour gérer les véhicules BLE, positions et alertes
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Import des modèles
from models import db, Vehicle, Location, Alert

load_dotenv()

# Initialisation Flask
app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/iot_parking'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
db.init_app(app)
CORS(app)

# ============ ROUTES D'ACCUEIL ============

@app.route('/', methods=['GET'])
def index():
    """API Info"""
    return jsonify({
        'message': 'Backend IoT Parking - Gestion des véhicules BLE',
        'version': '2.0.0',
        'endpoints': {
            'vehicles': 'GET /api/vehicles',
            'vehicle_by_tag': 'GET /api/vehicles/<tag_id>',
            'register_callback': 'GET /callback.html?device_id=<tag_id>',
            'associate_vehicle': 'POST /api/vehicles/associate',
            'positions': 'GET /api/positions',
            'positions_by_filters': 'GET /api/positions?zone=<zone>&status=<status>',
            'webhook': 'POST /webhook',
            'test_webhook': 'POST /test-webhook',
            'debug': 'GET /debug/status'
        }
    })


# ============ ASSOCIATION VÉHICULE/TAG BLE ============

@app.route('/callback.html', methods=['GET'])
def callback_page():
    """Page de callback - Formulaire d'association"""
    tag_id = request.args.get('device_id')
    if not tag_id:
        return jsonify({'error': 'device_id manquant'}), 400
    
    # Vérifier si le tag existe déjà
    vehicle = Vehicle.query.filter_by(ble_tag_id=tag_id).first()
    if vehicle:
        return jsonify({
            'message': 'Véhicule trouvé',
            'vehicle': vehicle.to_dict()
        }), 200
    
    return render_template('register_car.html', device_id=tag_id)


@app.route('/api/vehicles/associate', methods=['POST'])
def associate_vehicle():
    """Associer un tag BLE à un véhicule"""
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['ble_tag_id', 'vin', 'model', 'color', 'zone', 'delivery_date']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Champs manquants'}), 400
        
        # Vérifier si le tag existe déjà
        existing = Vehicle.query.filter_by(ble_tag_id=data['ble_tag_id']).first()
        if existing:
            return jsonify({'error': 'Ce tag BLE est déjà associé'}), 400
        
        # Créer le véhicule
        vehicle = Vehicle(
            ble_tag_id=data['ble_tag_id'],
            vin=data['vin'],
            model=data['model'],
            color=data['color'],
            fault_status=data.get('fault_status', False),
            zone=data['zone'],
            delivery_date=datetime.fromisoformat(data['delivery_date']).date(),
            customer=data.get('customer'),
            delivery_country=data.get('delivery_country'),
            expected_delivery_date=datetime.fromisoformat(data['expected_delivery_date']).date() if data.get('expected_delivery_date') else None,
            status=data.get('status', 'parked')

@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    """Récupérer tous les véhicules avec filtres"""
    try:
        # Filtres optionnels
        zone = request.args.get('zone')
        status = request.args.get('status')
        fault_status = request.args.get('fault_status')
        country = request.args.get('country')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        query = Vehicle.query
        
        if zone:
            query = query.filter_by(zone=zone)
        if status:
            query = query.filter_by(status=status)
        if fault_status:
            query = query.filter_by(fault_status=fault_status == 'true')
        if country:
            query = query.filter_by(delivery_country=country)
        
        total = query.count()
        vehicles = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'total': total,
            'limit': limit,
            'offset': offset,
            'vehicles': [v.to_dict() for v in vehicles]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vehicles/<tag_id>', methods=['GET'])
def get_vehicle(tag_id):
    """Récupérer un véhicule par tag BLE"""
    vehicle = Vehicle.query.filter_by(ble_tag_id=tag_id).first_or_404()
    
    # Récupérer la dernière position
    latest_location = Location.query.filter_by(
        ble_tag_id=tag_id,
        is_latest=True
    ).first()
    
    data = vehicle.to_dict()
    if latest_location:
        data['latest_location'] = latest_location.to_dict()
    
    return jsonify(data), 200


# ============ ENDPOINTS POSITIONS ============

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Récupérer les positions avec filtres"""
    try:
        zone = request.args.get('zone')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Query pour les dernières positions
        query = db.session.query(Vehicle, Location).join(
            Location, Vehicle.ble_tag_id == Location.ble_tag_id
        ).filter(Location.is_latest == True)
        
        if zone:
            query = query.filter(Vehicle.zone == zone)
        if status:
            query = query.filter(Vehicle.status == status)
        
        total = query.count()
        results = query.limit(limit).offset(offset).all()
        
        positions_data = []
        for vehicle, location in results:
            pos = location.to_dict()
            pos['vehicle'] = vehicle.to_dict()
            positions_data.append(pos)
        
        return jsonify({
            'total': total,
            'limit': limit,
            'offset': offset,
            'positions': positions_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/positions/<tag_id>', methods=['GET'])
def get_position_history(tag_id):
    """Récupérer l'historique des positions d'un véhicule"""
    limit = int(request.args.get('limit', 50))
    
    locations = Location.query.filter_by(ble_tag_id=tag_id).order_by(
        desc(Location.received_at)
    ).limit(limit).all()
    
    if not locations:
        return jsonify({'error': 'Aucune position trouvée'}), 404
    
    return jsonify({
        'ble_tag_id': tag_id,
        'history': [loc.to_dict() for loc in locations]
    }), 200


# ============ WEBHOOK BLE - RECEVOIR LES POSITIONS ============

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook pour recevoir les positions depuis BLEcon Cloud"""
    try:
        print("\n" + "="*70)
        print("🔔 WEBHOOK REÇU - Positions BLE du Cloud")
        print("="*70)
        
        data = request.json
        if not data:
            print("❌ Aucune donnée reçue")
            return {"status": "error", "message": "No data"}, 400
        
        print(f"📦 Données: {len(data)} événement(s)")
        
        events_processed = 0
        for event in data:
            if event.get("type") == "network.device_position":
                try:
                    tag_id = event["data"]["device_id"]
                    coords = event["data"]["geojson"]["geometry"]["coordinates"]  # [lon, lat]
                    accuracy = event["data"]["quality"]["accuracy_meters"]
                    battery = event["data"].get("battery_level")
                    movement = event["data"].get("movement_status", "static")
                    
                    # Vérifier que le véhicule existe
                    vehicle = Vehicle.query.filter_by(ble_tag_id=tag_id).first()
                    if not vehicle:
                        print(f"⚠️  Tag {tag_id} non associé")
                        continue
                    
                    # Marquer les anciennes positions comme non-latest
                    Location.query.filter_by(ble_tag_id=tag_id).update({'is_latest': False})
                    
                    # Créer la nouvelle position
                    location = Location(
                        ble_tag_id=tag_id,
                        latitude=coords[1],  # lat
                        longitude=coords[0],  # lon
                        accuracy=accuracy,
                        battery_level=battery,
                        movement_status=movement,
                        is_latest=True
                    )
                    
                    # Déterminer le statut du véhicule
                    if movement == "moving":
                        vehicle.status = "moved"
                    else:
                        vehicle.status = "parked"
                    
                    vehicle.updated_at = datetime.utcnow()
                    
                    db.session.add(location)
                    db.session.commit()
                    
                    print(f"✅ Position mise à jour: {vehicle.vin}")
                    print(f"   📍 Lat: {coords[1]:.6f}, Lon: {coords[0]:.6f}")
                    print(f"   📏 Précision: {accuracy}m")
                    events_processed += 1
                    
                except KeyError as ke:
                    print(f"⚠️  Clé manquante: {ke}")
                    continue
                except Exception as e:
                    print(f"⚠️  Erreur traitement: {e}")
                    db.session.rollback()
                    continue
        
        print(f"\n✅ {events_processed} position(s) mise(s) à jour")
        print("="*70 + "\n")
        
        return {"status": "ok", "events_processed": events_processed}, 200
        
    except Exception as e:
        print(f"❌ ERREUR WEBHOOK: {e}")
        print("="*70 + "\n")
        return {"status": "error", "message": str(e)}, 500


@app.route('/test-webhook', methods=['POST'])
def test_webhook():
    """Endpoint de test pour simuler l'envoi de positions"""
    try:
        # Données de test
        test_data = [
            {
                "type": "network.device_position",
                "data": {
                    "device_id": "urn:uuid:test-123",
                    "geojson": {
                        "geometry": {
                            "coordinates": [-3.9369, 5.3671]  # Casablanca
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
        
        print("🧪 TEST WEBHOOK - Données de simulation")
        
        # Appeler le webhook avec les test data
        with app.test_request_context(
            '/webhook',
            method='POST',
            json=test_data,
            content_type='application/json'
        ):
            response = webhook()
        
        return jsonify({
            'message': 'Test webhook exécuté',
            'test_data': test_data,
            'response': response
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ ENDPOINTS ALERTES ============

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Récupérer les alertes actives"""
    resolved = request.args.get('resolved', 'false') == 'true'
    limit = int(request.args.get('limit', 50))
    
    query = Alert.query.filter_by(is_resolved=resolved).order_by(desc(Alert.created_at))
    alerts = query.limit(limit).all()
    
    return jsonify({
        'total': len(alerts),
        'alerts': [a.to_dict() for a in alerts]
    }), 200


@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PATCH'])
def resolve_alert(alert_id):
    """Résoudre une alerte"""
    alert = Alert.query.get_or_404(alert_id)
    alert.is_resolved = True
    db.session.commit()
    
    return jsonify({
        'message': 'Alerte résolue',
        'alert': alert.to_dict()
    }), 200


# ============ ENDPOINTS DEBUG ============

@app.route('/debug/status', methods=['GET'])
def debug_status():
    """Statut global du système"""
    try:
        total_vehicles = Vehicle.query.count()
        total_positions = Location.query.count()
        total_alerts = Alert.query.count()
        unresolved_alerts = Alert.query.filter_by(is_resolved=False).count()
        
        zones = db.session.query(Vehicle.zone, func.count(Vehicle.id)).group_by(Vehicle.zone).all()
        
        return jsonify({
            'status': 'running',
            'database': 'connected',
            'vehicles': {
                'total': total_vehicles,
                'by_zone': [{'zone': z[0], 'count': z[1]} for z in zones]
            },
            'positions': {
                'total': total_positions,
                'latest': Location.query.filter_by(is_latest=True).count()
            },
            'alerts': {
                'total': total_alerts,
                'unresolved': unresolved_alerts
            },
            'webhook_url': 'POST /webhook',
            'callback_url': 'GET /callback.html?device_id=<tag_id>'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500


# ============ GESTION D'ERREURS ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Erreur serveur'}), 500


# ============ INITIALISATION ============

if __name__ == '__main__':
    with app.app_context():
        print("🚀 Initialisation du serveur...")
        print(f"📊 Base de données: {os.getenv('DATABASE_URL', 'postgresql://localhost:5432/iot_parking')}")
        
        # Créer les tables si elles n'existent pas
        db.create_all()
        print("✅ Tables vérifiées/créées")
        
        print("\n🚗 Backend IoT Parking démarré!")
        print("📍 Accédez à: http://localhost:8000")
        print("🔗 Webhook: POST http://localhost:8000/webhook")
        print("🗺️  Callback: GET http://localhost:8000/callback.html\n")
        
        app.run(host='0.0.0.0', port=8000, debug=True)

# ============ ROUTES PRINCIPALES ============

@app.route('/', methods=['GET'])
def index():
    """Page d'accueil"""
    return jsonify({
        'message': 'Bienvenue sur l\'API IoT Parking Solution',
        'version': '1.1.0',
        'endpoints': {
            'register_car_page': '/register-car-page?device_id=<device_id>',
            'register_car': 'POST /register-car',
            'get_cars': 'GET /api/cars',
            'get_car': 'GET /api/cars/<device_id>',
            'positions': 'GET /positions',
            'locations': 'GET /api/locations',
            'map': 'GET /map',
            'blecon_webhook': 'POST /webhook'
        }
    })

@app.route('/map', methods=['GET'])
def map_page():
    """Page carte avec positions des voitures"""
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    return jsonify({'error': 'Fichier index.html non trouvé'}), 404

@app.route('/register-car-page', methods=['GET'])
def register_car_page():
    """Page d'enregistrement de voiture (formulaire HTML)"""
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({'error': 'device_id manquant'}), 400
    return render_template('register_car.html', device_id=device_id)

@app.route('/callback.html', methods=['GET'])
def callback():
    """Callback page pour l'enregistrement de voiture"""
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({'error': 'device_id manquant'}), 400
    return render_template('register_car.html', device_id=device_id)

@app.route('/register-car', methods=['POST'])
def register_car():
    """Enregistrer une voiture avec son tag IoT"""
    try:
        data = request.get_json()
        required_fields = ['device_id', 'plate', 'make', 'model']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Champs manquants'}), 400

        if data['device_id'] in cars_db:
            return jsonify({'error': 'Ce device_id est déjà enregistré'}), 400

        car = {
            'id': len(cars_db) + 1,
            'device_id': data['device_id'],
            'plate': data['plate'],
            'make': data['make'],
            'model': data['model'],
            'color': data.get('color'),
            'year': data.get('year'),
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }

        cars_db[data['device_id']] = car
        return jsonify({'message': 'Voiture enregistrée avec succès', 'car': car}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ BLECON WEBHOOK - RÉCUPÉRATION DES POSITIONS ============

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook pour recevoir les positions des tags BLE depuis le cloud BLEcon
    Format attendu: Array d'événements avec type "network.device_position"
    """
    try:
        print("\n" + "="*60)
        print("🔔 WEBHOOK REÇU du cloud BLE")
        print("="*60)
        
        # Récupérer les données brutes
        data = request.json
        print(f"📦 Données brutes reçues: {json.dumps(data, indent=2)}")
        
        if not data:
            print("❌ Aucune donnée dans la requête")
            return {"status": "error", "message": "No data received"}, 400
        
        # Traiter chaque événement reçu
        events_processed = 0
        for event in data:
            print(f"\n📌 Événement traité: {event.get('type')}")
            
            if event.get("type") == "network.device_position":
                try:
                    device_id = event["data"]["device_id"]
                    coords = event["data"]["geojson"]["geometry"]["coordinates"]  # [lon, lat]
                    accuracy = event["data"]["quality"]["accuracy_meters"]
                    
                    # Stocker la position avec timestamp et précision
                    positions[device_id] = {
                        "longitude": coords[0],
                        "latitude": coords[1],
                        "accuracy": accuracy,
                        "last_seen": datetime.utcnow().isoformat()
                    }
                    
                    print(f"✅ Position mise à jour pour {device_id}")
                    print(f"   📍 Lat: {coords[1]}, Lon: {coords[0]}")
                    print(f"   📏 Précision: {accuracy}m")
                    events_processed += 1
                    
                except KeyError as ke:
                    print(f"⚠️  Clé manquante: {ke}")
                except Exception as e:
                    print(f"⚠️  Erreur traitement événement: {e}")
        
        print(f"\n✅ {events_processed} position(s) mise(s) à jour")
        print(f"📊 Total positions en mémoire: {len(positions)}")
        print("="*60 + "\n")
        
        return {"status": "ok", "events_processed": events_processed}, 200
        
    except Exception as e:
        print(f"\n❌ ERREUR WEBHOOK: {e}")
        print("="*60 + "\n")
        return {"status": "error", "message": str(e)}, 500


@app.route('/test-webhook', methods=['POST'])
def test_webhook():
    """
    Endpoint de TEST pour simuler l'envoi de données BLE depuis le cloud
    Utilisé pour déboguer sans attendre les vraies données du cloud
    """
    try:
        # Données de test simulées
        test_data = [
            {
                "type": "network.device_position",
                "data": {
                    "device_id": "urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d",
                    "geojson": {
                        "geometry": {
                            "coordinates": [-3.9369, 5.3671]  # Lon, Lat (Casablanca, Maroc)
                        }
                    },
                    "quality": {
                        "accuracy_meters": 45
                    }
                }
            }
        ]
        
        print("\n🧪 TEST WEBHOOK - Envoi de données de test")
        # Appeler le webhook avec les données de test
        response = webhook()
        
        return jsonify({
            'message': 'Test webhook envoyé avec succès',
            'test_data': test_data,
            'positions': positions
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/debug/positions', methods=['GET'])
def debug_positions():
    """Endpoint de DEBUG pour voir les positions stockées"""
    return jsonify({
        'total': len(positions),
        'positions': positions,
        'cars': cars_db
    })


@app.route('/debug/webhook-status', methods=['GET'])
def debug_webhook_status():
    """Endpoint pour vérifier l'état du webhook"""
    return jsonify({
        'webhook_url': request.host_url + 'webhook',
        'test_url': request.host_url + 'test-webhook',
        'positions_received': len(positions),
        'cars_registered': len(cars_db),
        'status': 'running',
        'message': 'Webhook en attente de données depuis le cloud BLE. Utilisez /test-webhook pour tester.'
    })

# ============ ENDPOINT POUR RÉCUPÉRER LES POSITIONS ============

@app.route('/positions', methods=['GET'])
def get_positions():
    """Récupérer toutes les positions des véhicules"""
    return jsonify(positions)

@app.route('/positions/<device_id>', methods=['GET'])
def get_position(device_id):
    """Récupérer la position d'un véhicule spécifique"""
    if device_id not in positions:
        return jsonify({'error': 'Aucune position trouvée pour ce device_id'}), 404
    return jsonify({
        'device_id': device_id,
        **positions[device_id]
    })

# ============ ENDPOINTS CARS ============

@app.route('/api/cars', methods=['GET'])
def get_cars():
    """Récupérer toutes les voitures enregistrées"""
    cars_with_position = []
    for car in cars_db.values():
        car_data = car.copy()
        if car['device_id'] in positions:
            car_data['position'] = positions[car['device_id']]
        cars_with_position.append(car_data)
    return jsonify(cars_with_position)

@app.route('/api/locations', methods=['GET'])
def get_locations():
    """Endpoint pour le frontend - format compatible avec la carte"""
    locations = []
    for car in cars_db.values():
        if car['device_id'] in positions:
            pos = positions[car['device_id']]
            locations.append({
                'device_id': car['device_id'],
                'lat': pos['latitude'],
                'lon': pos['longitude'],
                'accuracy': pos['accuracy'],
                'last_seen': pos['last_seen'],
                'car_info': {
                    'plate': car['plate'],
                    'make': car['make'],
                    'model': car['model'],
                    'color': car.get('color'),
                    'year': car.get('year')
                }
            })
    return jsonify(locations)

@app.route('/api/cars/<device_id>', methods=['GET'])
def get_car(device_id):
    """Récupérer les infos d'une voiture avec sa position"""
    if device_id not in cars_db:
        return jsonify({'error': 'Voiture non trouvée'}), 404
    
    car_data = cars_db[device_id].copy()
    if device_id in positions:
        car_data['position'] = positions[device_id]
    
    return jsonify(car_data)

# ============ GESTION D'ERREURS ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur serveur'}), 500

# ============ INITIALISATION ============

if __name__ == '__main__':
    print("🚗 Démarrage du serveur IoT Parking...")
    print("Accédez à: http://localhost:8000")
    print("📍 Webhook BLEcon: POST http://localhost:8000/webhook")
    app.run(host='0.0.0.0', port=8000, debug=True)