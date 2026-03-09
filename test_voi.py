import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("PHASE 1: CRÉATION DE LA VOITURE")
print("=" * 60)

# Données de la voiture - SANS device_id !
vehicle_data = {
    "vin": "1HGCM82633A004352",
    "model": "Honda Civic",
    "color": "Red",
    "zone": "Zone A",
    "entry_date": "2026-03-01",
    "delivery_date": "2026-03-10",
    "customer": "John Doe",
    "delivery_country": "Tunisia",
    "expected_delivery_date": "2026-03-10"
    # ⚠️ NE PAS METTRE device_id ici !
}

print("\n📦 Données envoyées:")
print(json.dumps(vehicle_data, indent=2))

try:
    # Envoyer la requête
    response = requests.post(f"{BASE_URL}/cars", json=vehicle_data)
    
    print(f"\n📡 Statut: {response.status_code}")
    
    if response.status_code == 200:
        vehicle = response.json()
        print("\n✅ SUCCÈS! Voiture créée:")
        print(json.dumps(vehicle, indent=2))
        
        # Sauvegarder l'ID pour les phases suivantes
        with open("vehicle_id.txt", "w") as f:
            f.write(str(vehicle["id"]))
        print(f"\n💾 ID sauvegardé: {vehicle['id']} (dans vehicle_id.txt)")
    else:
        print(f"\n❌ Erreur: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ Impossible de se connecter au serveur!")
    print("Vérifiez que le serveur tourne sur http://127.0.0.1:8000")
except Exception as e:
    print(f"\n❌ Erreur: {e}")

print("\n" + "=" * 60)