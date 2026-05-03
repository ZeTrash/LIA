# Interface Web LIA - Débats en Temps Réel

Interface web pour suivre les débats LIA-Gemini en temps réel via WebSocket.

## Installation

```bash
cd /opt/LIA
source venv/bin/activate
pip install -r web_interface/requirements.txt
```

## Lancement

```bash
cd /opt/LIA
source venv/bin/activate
python web_interface/app.py
```

Ou avec uvicorn directement :

```bash
cd /opt/LIA
source venv/bin/activate
uvicorn web_interface.app:app --host 0.0.0.0 --port 8000 --reload
```

## Utilisation

1. Ouvrir un navigateur à l'adresse : `http://localhost:8000`
2. Entrer une thématique dans le champ de texte
3. Cliquer sur "Démarrer le débat"
4. Suivre le débat en temps réel dans l'interface

## Fonctionnalités

- ✅ Affichage en temps réel via WebSocket
- ✅ Suivi étape par étape (thèse, antithèse, débat, synthèse)
- ✅ Scores de qualité affichés
- ✅ Distance sémantique thèse/antithèse
- ✅ Interface simple et claire

## Architecture

- **FastAPI** : Serveur web asynchrone
- **WebSocket** : Communication bidirectionnelle en temps réel
- **HTML/CSS/JavaScript** : Interface client



