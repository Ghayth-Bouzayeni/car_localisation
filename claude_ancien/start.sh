#!/bin/bash
# Script de démarrage complet du backend

echo "🚗 IoT Parking Backend - Setup & Launch"
echo "========================================"

# Vérifier Python
echo "✓ Vérification Python..."
python --version || { echo "❌ Python non installé"; exit 1; }

# Vérifier PostgreSQL
echo "✓ Vérification PostgreSQL..."
psql --version || { echo "⚠️  PostgreSQL non installé (optionnel)"; }

# Installer les dépendances
echo "✓ Installation des dépendances..."
pip install -q -r requirements.txt

# Créer la base de données
echo "✓ Création du schéma PostgreSQL..."
python create_db.py

# Lancer le serveur
echo ""
echo "✅ Prêt! Démarrage du serveur..."
echo ""
echo "🌐 Frontend: http://localhost:8000/map"
echo "📝 Callback: http://localhost:8000/callback.html?device_id=YOUR_TAG"
echo "🔗 API: http://localhost:8000/api/vehicles"
echo "🪝 Webhook: http://localhost:8000/webhook"
echo ""

python server.py
