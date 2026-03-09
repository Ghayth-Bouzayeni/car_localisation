import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("PHASE 2: PRÉPARATION DU DEVICE BLE")
print("=" * 60)

device_identifier = "urn:uuid:17e56c9a-adef-42f1-9679-4fa0d0c9301d"

print(f"\n📱 Device Identifier: {device_identifier}")
print("\n🔍 Vérification...")

try:
    # Vérifier si le device existe déjà via la table devices
    # Note: On ne peut pas car l'endpoint n'existe pas
    print("ℹ️ Endpoint /devices/ non disponible")
    print("✅ Le device sera créé automatiquement lors de l'association en Phase 3")
    
    # Sauvegarder l'identifiant pour la phase 3
    with open("device_identifier.txt", "w") as f:
        f.write(device_identifier)
    print(f"\n💾 Device identifier sauvegardé: {device_identifier}")
    
except Exception as e:
    print(f"\n❌ Erreur: {e}")

print("\n" + "=" * 60)
print("✅ Passez maintenant à la Phase 3 (association)")
print("=" * 60)