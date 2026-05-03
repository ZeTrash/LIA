#!/bin/bash
# Script de lancement de l'interface web LIA

cd /opt/LIA
source venv/bin/activate

echo "🚀 Démarrage de l'interface web LIA..."
echo "📡 Serveur accessible sur: http://localhost:8008"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

python web_interface/app.py

