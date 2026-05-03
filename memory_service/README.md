# Memory Service - Phase 3

Service mémoire persistante pour LIA.

## Structure

```
memory_service/
├── __init__.py
├── models.py              # Modèles SQLAlchemy (Traits, Souvenirs, Interactions)
├── db.py                  # Gestion base de données SQLite
├── store.py               # Logique métier
├── memory_adapter.py      # Adaptateur pour intégration avec noyau primaire
├── api.py                 # API REST FastAPI
├── requirements.txt       # Dépendances
└── tests/
    └── test_memory.py     # Tests unitaires
```

## Installation

```bash
cd /opt/LIA
source venv/bin/activate
pip install -r memory_service/requirements.txt
```

## Utilisation

### API REST

Lancer le serveur :

```bash
cd /opt/LIA
source venv/bin/activate
uvicorn memory_service.api:app --reload
```

Endpoints disponibles :
- `GET /context` : Récupère le contexte mémoire (traits + souvenirs)
- `POST /trait` : Crée ou met à jour un trait
- `POST /memory` : Crée un souvenir
- `POST /interaction` : Journalise une interaction
- `GET /health` : Vérification de santé

### Intégration avec le Noyau Primaire

Le `LLMAdapter` intègre automatiquement la mémoire si disponible :

```python
from core import LLMAdapter, CoreConfig

# La mémoire est activée par défaut
adapter = LLMAdapter(CoreConfig())

# Générer une réponse (contexte récupéré automatiquement depuis mémoire)
response = await adapter.generate("Bonjour", session_id="session_123")
```

## Base de Données

La base de données SQLite est créée automatiquement dans `data/memory.db`.

### Modèles

- **Traits** : Traits de personnalité (persona, skill, style, constraint)
- **Souvenirs** : Mémoires avec scores (importance, récence, émotion)
- **Interactions** : Logs des interactions utilisateur

## Tests

```bash
cd /opt/LIA
source venv/bin/activate
pytest memory_service/tests/
```

## Nettoyage de la Base de Données

Pour nettoyer la base de données (supprimer toutes les données de test) :

```bash
cd /opt/LIA
source venv/bin/activate

# Avec confirmation
python memory_service/clean_db.py

# Sans confirmation (automatique)
python memory_service/clean_db.py --yes
```

**Note** : Le nettoyage supprime toutes les données (traits, souvenirs, interactions) mais conserve la structure des tables.

## Phase 3 - Statut

✅ **Phase 3.1 : Service Mémoire de Base** - Terminé
- ✅ Modèles de données (Traits, Souvenirs, Interactions)
- ✅ Base de données SQLite
- ✅ API REST basique
- ✅ Tests de base

✅ **Phase 3.2 : Intégration Noyau Primaire ↔ Mémoire** - Terminé
- ✅ Récupération du contexte depuis mémoire
- ✅ Journalisation des interactions
- ✅ Adaptateur mémoire pour intégration

