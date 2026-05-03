# 🚀 Démarrage Rapide - Interface Web LIA

## Lancement

```bash
cd /opt/LIA
source venv/bin/activate
python web_interface/app.py
```

Ou avec le script :

```bash
./web_interface/start.sh
```

## Accès

Ouvrir dans votre navigateur :
- **Local** : http://localhost:8000
- **Réseau** : http://<votre-ip>:8000

## Utilisation

1. Entrer une thématique (ex: "L'intelligence artificielle va-t-elle remplacer les humains au travail ?")
2. Cliquer sur "Démarrer le débat"
3. Suivre le débat en temps réel dans l'interface

## Fonctionnalités

✅ Affichage en temps réel via WebSocket
✅ Suivi étape par étape
✅ Scores de qualité
✅ Distance sémantique
✅ Interface claire et simple

## Dépannage

Si le port 8000 est occupé, modifier dans `app.py` :
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Changer le port
```
