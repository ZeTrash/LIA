# Interface Web de Chat avec LIA

Interface web moderne pour converser avec LIA en temps réel via WebSocket.

## 🚀 Démarrage Rapide

### Option 1 : Script de démarrage (recommandé)

```bash
cd web_interface
./start_chat.sh
```

### Option 2 : Démarrage manuel

```bash
cd web_interface
source ../venv/bin/activate
python app_chat.py --host 127.0.0.1 --port 8001
```

### Option 3 : Avec uvicorn directement

```bash
cd web_interface
source ../venv/bin/activate
uvicorn app_chat:app --host 127.0.0.1 --port 8001 --reload
```

## 🌐 Accès à l'Interface

Une fois le serveur démarré, ouvrez votre navigateur et accédez à :

```
http://127.0.0.1:8001
```

## ✨ Fonctionnalités

### Chat en Temps Réel
- ✅ Conversations fluides avec LIA
- ✅ Interface moderne et responsive
- ✅ Indicateur de connexion en temps réel
- ✅ Animation de réflexion pendant la génération

### Autonomie
- ✅ LIA peut solliciter automatiquement Gemini pour des questions complexes
- ✅ Intégration transparente du canal Support
- ✅ Fallback automatique si Gemini n'est pas disponible

### Gestion de Session
- ✅ Session unique par onglet/navigateur
- ✅ Historique des conversations
- ✅ Journalisation automatique dans la mémoire

### Interface Utilisateur
- ✅ Design moderne avec dégradés
- ✅ Messages avec avatars
- ✅ Indicateur de connexion
- ✅ Responsive (mobile et desktop)
- ✅ Animations fluides

## 📋 Prérequis

1. **Modèle LLM** : Le modèle `Llama-3.2-3B-Instruct-Q4_K_M.gguf` doit être présent dans `models/`
2. **Environnement virtuel** : Activé avec les dépendances installées
3. **Configuration API (optionnel)** : Pour l'autonomie avec Gemini, configurer `config/api.conf`

## 🔧 Configuration

### Port et Adresse

Modifier le port ou l'adresse dans le script de démarrage ou via les arguments :

```bash
python app_chat.py --host 0.0.0.0 --port 8080
```

### Autonomie (Gemini)

Pour activer l'autonomie de LIA (sollicitation automatique de Gemini) :

1. Créer/modifier `config/api.conf` :
```ini
[gemini]
api_key = VOTRE_CLE_API_GEMINI
```

2. L'interface détectera automatiquement la configuration au démarrage

## 📁 Structure des Fichiers

```
web_interface/
├── app_chat.py          # Application FastAPI principale
├── start_chat.sh        # Script de démarrage
├── static/
│   └── chat.html        # Interface HTML/CSS/JS
└── README_CHAT.md       # Ce fichier
```

## 🧪 Tests

### Test de Connexion

Vérifier que le serveur répond :

```bash
curl http://127.0.0.1:8001/health
```

Réponse attendue :
```json
{
  "status": "ok",
  "user_channel_initialized": true,
  "timestamp": "2024-12-19T..."
}
```

### Test WebSocket

Utiliser un client WebSocket pour tester la connexion :

```bash
# Avec wscat (npm install -g wscat)
wscat -c ws://127.0.0.1:8001/ws/test_session
```

Envoyer un message :
```json
{"type": "message", "content": "Bonjour LIA !"}
```

## 🐛 Dépannage

### Le serveur ne démarre pas

1. Vérifier que le modèle existe : `ls models/Llama-3.2-3B-Instruct-Q4_K_M.gguf`
2. Vérifier les dépendances : `pip install -r requirements.txt`
3. Vérifier les logs pour les erreurs

### LIA ne répond pas

1. Vérifier les logs du serveur
2. Vérifier que le modèle est chargé (message dans les logs)
3. Vérifier la connexion WebSocket dans la console du navigateur (F12)

### Erreur de connexion WebSocket

1. Vérifier que le serveur est bien démarré
2. Vérifier le port (8001 par défaut)
3. Vérifier les pare-feu/proxy

## 📝 Notes

- **Performance** : Le premier chargement du modèle peut prendre quelques secondes
- **Mémoire** : Le modèle nécessite environ 2-3 GB de RAM
- **Sessions** : Chaque onglet/navigateur crée une session unique
- **Historique** : L'historique est conservé en mémoire pendant la session

## 🔄 Différences avec l'Interface de Débat

| Fonctionnalité | Interface Chat | Interface Débat |
|----------------|----------------|-----------------|
| **Usage** | Conversation libre | Débat structuré LIA-Gemini |
| **Port** | 8001 | 8000 |
| **Fichier** | `app_chat.py` | `app.py` |
| **Canal** | UserChannel | Direct LLMAdapter |
| **Autonomie** | ✅ Oui (via SupportChannel) | ❌ Non |

## 🚀 Prochaines Améliorations

- [ ] Sauvegarde de l'historique dans la base de données
- [ ] Export des conversations
- [ ] Mode sombre
- [ ] Notifications sonores
- [ ] Partage de session
- [ ] Commandes spéciales (/clear, /history, /stats)

---

**Créé le** : 2024-12-19  
**Version** : 1.0.0

