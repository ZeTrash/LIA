# Guide de Test - Phase 3 : Mémoire

Ce guide explique comment tester le service mémoire et son intégration avec le noyau primaire.

## Prérequis

1. Installer les dépendances :
```bash
cd /opt/LIA
source venv/bin/activate
pip install -r memory_service/requirements.txt
```

2. Vérifier que le modèle est téléchargé :
```bash
ls -la models/Qwen/Qwen2.5-1.5B-Instruct/
```

## Tests Disponibles

### 1. Tests Unitaires

Exécuter les tests unitaires du service mémoire :

```bash
cd /opt/LIA
source venv/bin/activate
pytest memory_service/tests/test_memory.py -v
```

**Résultat attendu** : Tous les tests passent (test_add_trait, test_add_memory, test_log_interaction, test_get_context)

### 2. Test de l'API REST

#### 2.1. Démarrer le serveur API

Dans un terminal :
```bash
cd /opt/LIA
source venv/bin/activate
uvicorn memory_service.api:app --reload --port 8000
```

#### 2.2. Tester les endpoints

Dans un autre terminal, tester avec `curl` ou un navigateur :

**a) Vérifier la santé du service :**
```bash
curl http://localhost:8000/health
```

**b) Récupérer le contexte (vide au début) :**
```bash
curl http://localhost:8000/context
```

**c) Ajouter un trait :**
```bash
curl -X POST http://localhost:8000/trait \
  -H "Content-Type: application/json" \
  -d '{
    "type": "persona",
    "label": "curiosité",
    "value": "très curieux et avide d apprendre",
    "weight": 0.9,
    "confidence": 0.8
  }'
```

**d) Ajouter un souvenir :**
```bash
curl -X POST http://localhost:8000/memory \
  -H "Content-Type: application/json" \
  -d '{
    "category": "fact",
    "content": "L utilisateur aime le café et la programmation",
    "tags": ["préférence", "hobby"],
    "importance_score": 0.7,
    "ttl_days": 30
  }'
```

**e) Récupérer le contexte (maintenant avec données) :**
```bash
curl http://localhost:8000/context
```

**f) Journaliser une interaction :**
```bash
curl -X POST http://localhost:8000/interaction \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "prompt": "Bonjour",
    "response": "Bonjour ! Comment puis-je vous aider ?",
    "severity": "info"
  }'
```

### 3. Test d'Intégration Mémoire + Noyau Primaire

Exécuter le script de test d'intégration :

```bash
cd /opt/LIA
source venv/bin/activate
python memory_service/test_integration.py
```

**Ce test vérifie :**
- ✅ Ajout de traits et souvenirs dans la mémoire
- ✅ Récupération du contexte
- ✅ Initialisation du noyau primaire avec mémoire
- ✅ Génération d'une réponse avec contexte mémoire
- ✅ Journalisation automatique des interactions

### 4. Test Manuel avec Chat

Tester l'intégration complète avec le script de chat :

```bash
cd /opt/LIA
source venv/bin/activate
python core/test_chat.py
```

**Pendant le chat :**
1. Les interactions sont automatiquement journalisées
2. Le contexte mémoire est utilisé pour générer les réponses
3. Vous pouvez ajouter des traits/souvenirs via l'API REST et voir l'impact sur les réponses

### 5. Vérification de la Base de Données

Inspecter la base de données SQLite :

```bash
cd /opt/LIA
source venv/bin/activate
sqlite3 data/memory.db

# Dans SQLite :
.tables
SELECT * FROM traits;
SELECT * FROM souvenirs;
SELECT * FROM interaction_logs;
.quit
```

## Tests Python Interactifs

### Test Rapide du Store

```python
from memory_service import MemoryStore

store = MemoryStore()

# Ajouter un trait
trait_id = store.add_trait("persona", "amabilité", "très amical", 0.8)
print(f"Trait ajouté: {trait_id}")

# Ajouter un souvenir
memory_id = store.add_memory("preference", "Aime les chats", ["animaux"], 0.6)
print(f"Souvenir ajouté: {memory_id}")

# Récupérer le contexte
context = store.get_context()
print(f"Contexte: {len(context['traits'])} traits, {len(context['memories'])} souvenirs")
```

### Test de l'Adaptateur Mémoire

```python
from memory_service import MemoryAdapter

adapter = MemoryAdapter()

# Récupérer le contexte
context = adapter.get_context()
print(f"Contexte: {len(context['traits'])} traits, {len(context['memories'])} souvenirs")

# Journaliser une interaction
interaction_id = adapter.log_interaction(
    session_id="test_123",
    prompt="Bonjour",
    response="Bonjour !"
)
print(f"Interaction journalisée: {interaction_id}")
```

### Test d'Intégration Complète

```python
import asyncio
from core import LLMAdapter, CoreConfig
from memory_service import MemoryStore

# Ajouter des données dans la mémoire
store = MemoryStore()
store.add_trait("persona", "curiosité", "très curieux", 0.9)
store.add_memory("fact", "Aime le café", ["préférence"], 0.7)

# Créer l'adaptateur avec mémoire
config = CoreConfig(
    model_path="models/Qwen/Qwen2.5-1.5B-Instruct",
    quantize=True,
    quantization_bits=4
)

async def test():
    adapter = LLMAdapter(config, use_memory=True)
    
    # Générer une réponse (contexte récupéré automatiquement)
    response = await adapter.generate(
        "Qui suis-je ?",
        session_id="test_session"
    )
    print(f"Réponse: {response}")

asyncio.run(test())
```

## Vérification des Résultats

### ✅ Critères de Validation Phase 3.1

- [ ] Base de données créée dans `data/memory.db`
- [ ] Modèles fonctionnent (traits, souvenirs, interactions)
- [ ] API REST basique fonctionne (tous les endpoints répondent)
- [ ] Tests unitaires passent

### ✅ Critères de Validation Phase 3.2

- [ ] Noyau primaire récupère le contexte depuis mémoire
- [ ] Interactions sont journalisées automatiquement
- [ ] Test d'intégration passe

## Dépannage

### Erreur : "Service mémoire non disponible"

**Solution** : Vérifier que les dépendances sont installées :
```bash
pip install -r memory_service/requirements.txt
```

### Erreur : "Base de données verrouillée"

**Solution** : Fermer toutes les connexions et réessayer. SQLite avec WAL supporte plusieurs connexions simultanées.

### Erreur : "Modèle non trouvé"

**Solution** : Télécharger le modèle :
```bash
python core/download_model.py
```

### Erreur lors de l'intégration mémoire

**Solution** : Désactiver temporairement la mémoire pour tester :
```python
adapter = LLMAdapter(config, use_memory=False)
```

## Prochaines Étapes

Une fois la Phase 3 validée, vous pouvez passer à la **Phase 4 : Noyau d'Appui (Gemini)**.

