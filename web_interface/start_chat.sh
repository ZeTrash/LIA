#!/bin/bash

# Script de démarrage de l'interface web de chat avec LIA

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Démarrage de l'interface web de chat avec LIA..."
echo ""

# Activer l'environnement virtuel
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "✅ Activation de l'environnement virtuel..."
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo "⚠️  Environnement virtuel non trouvé. Création..."
    python3 -m venv "$PROJECT_ROOT/venv"
    source "$PROJECT_ROOT/venv/bin/activate"
    pip install -r "$SCRIPT_DIR/requirements.txt"
fi

# Vérifier que le modèle existe
MODEL_PATH="$PROJECT_ROOT/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
if [ ! -f "$MODEL_PATH" ]; then
    echo "⚠️  Modèle non trouvé: $MODEL_PATH"
    echo "   Veuillez télécharger le modèle avant de continuer."
    exit 1
fi

# Changer vers le répertoire web_interface
cd "$SCRIPT_DIR"

# Démarrer le serveur
echo "✅ Démarrage du serveur web..."
echo ""
echo "🌐 Interface disponible sur: http://127.0.0.1:8001"
echo "   Appuyez sur Ctrl+C pour arrêter le serveur"
echo ""

python app_chat.py --host 127.0.0.1 --port 8001

