import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("PHASE 3: ASSOCIATION VOITURE ↔ DEVICE")
print("=" * 60)

# Récupérer l'ID de la voiture depuis la phase 1
try:
    with open("vehicle_id.txt", "r") as f:
        vehicle_id = int(f.read().strip())
    print(f"\n🚗 Vehicle ID chargé: {vehicle_id}")
except FileNotFoundError:
    print("\n❌ Fichier vehicle_id.txt non trouvé!")
    print("Exécutez d'abord phase1_create_car.py")
    exit(1)

# Récupérer l'identifiant du device depuis la phase 2
try:
    with open("device_identifier.txt", "r") as f:
        device_identifier = f.read().strip()
    print(f"📱 Device Identifier chargé: {device_identifier}")
except FileNotFoundError:
    print("\n⚠️ Fichier device_identifier.txt non trouvé!")
    device_identifier = "urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d"
    print(f"📱 Utilisation du défaut: {device_identifier}")

print("\n📦 Paramètres d'association (dans l'URL):")
print(f"   vehicle_id = {vehicle_id}")
print(f"   device_identifier = {device_identifier}")

try:
    # ⚠️ IMPORTANT: Les paramètres vont dans l'URL, pas dans le body JSON
    response = requests.post(
        f"{BASE_URL}/associate",
        params={  # 👈 Utiliser 'params' pour les query parameters
            "vehicle_id": vehicle_id,
            "device_identifier": device_identifier
        }
    )
    
    print(f"\n📡 Statut: {response.status_code}")
    print(f"📡 URL appelée: {response.url}")
    
    if response.status_code == 200:
        association = response.json()
        print("\n✅ SUCCÈS! Association effectuée:")
        print(json.dumps(association, indent=2))
        
        # Vérification
        print("\n🔍 Vérification de la voiture après association...")
        car_response = requests.get(f"{BASE_URL}/cars/{vehicle_id}")
        
        if car_response.status_code == 200:
            car = car_response.json()
            print(f"\n✅ Voiture trouvée:")
            print(f"   ID: {car['id']}")
            print(f"   VIN: {car['vin']}")
            print(f"   Modèle: {car['model']}")
            
            # Vérifier l'association via un autre endpoint si disponible
            print("\n🔍 Vérification de l'association...")
            # Note: Vous pourriez avoir besoin d'un endpoint pour vérifier l'association
    else:
        print(f"\n❌ Erreur: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ Impossible de se connecter au serveur!")
    print("Vérifiez que le serveur tourne sur http://127.0.0.1:8000")
except Exception as e:
    print(f"\n❌ Erreur: {e}")

print("\n" + "=" * 60)