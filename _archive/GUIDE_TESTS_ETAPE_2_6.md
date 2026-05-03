# Guide de Tests - Étape 2.6

## Tests disponibles

### Memory Service (Objectifs personnels)

**Fichier de test** : `memory_service/tests/test_personal_goals.py`

**Tests inclus** :
- ✅ Test des schémas Pydantic (PersonalGoal, PersonalGoalCreate, PersonalGoalUpdate)
- ✅ Test de création d'objectif
- ✅ Test de récupération (tous, par ID, avec filtres)
- ✅ Test de mise à jour
- ✅ Test de suppression
- ✅ Test de récupération des objectifs à déclencher

**Lancer les tests** :
```powershell
cd memory_service
python run_tests.py
```

**Ou directement** :
```powershell
cd memory_service
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_personal_goals.py -v
```

### Simulation Service (Scheduler et Portails)

**Fichier de test** : `simulation_service/tests/test_autonomous_scheduler.py`

**Tests inclus** :
- ✅ Test d'initialisation du scheduler
- ✅ Test du statut
- ✅ Test de vérification des objectifs personnels
- ✅ Test de déclenchement auto-recherche
- ✅ Test de déclenchement auto-évaluation
- ✅ Test de déclenchement auto-réflexion
- ✅ Test de gestion d'erreurs (_safe_execute)
- ✅ Test d'arrêt du scheduler

**Lancer les tests** :
```powershell
cd simulation_service
python run_tests.py
```

**Ou directement** :
```powershell
cd simulation_service
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_autonomous_scheduler.py -v
```

## Tests de tous les composants

### Tous les tests (simulation_service)
```powershell
cd simulation_service
python run_tests.py
```

### Tous les tests (memory_service)
```powershell
cd memory_service
python run_tests.py
```

## Tests spécifiques

### Tests des objectifs personnels uniquement
```powershell
cd memory_service
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_personal_goals.py -v
```

### Tests du scheduler uniquement
```powershell
cd simulation_service
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_autonomous_scheduler.py -v
```

### Tests existants (protocole, métriques, API)
```powershell
cd simulation_service
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_protocol.py tests/test_metrics.py tests/test_api.py -v
```

## Vérifications préalables

1. **Dépendances installées** :
   ```powershell
   # Memory Service
   cd memory_service
   pip install -r requirements.txt
   
   # Simulation Service
   cd simulation_service
   pip install -r requirements-test.txt  # Pour tests de base
   # ou
   pip install -r requirements.txt  # Pour toutes les dépendances
   ```

2. **Base de données** : Les tests utilisent `sqlite:///:memory:` (base en mémoire), donc pas de configuration nécessaire.

## Résultats attendus

### Memory Service
- **8 tests** pour les objectifs personnels
- Tous devraient passer ✅

### Simulation Service
- **9 tests** pour le scheduler autonome
- Tous devraient passer ✅
- Les tests utilisent des mocks pour éviter les dépendances externes

## Notes importantes

- Les tests du scheduler utilisent des **mocks** pour éviter de démarrer réellement le scheduler
- Les tests des objectifs personnels utilisent une **base de données en mémoire** (SQLite)
- Les tests sont **asynchrones** (utilisent `pytest-asyncio`)

## Dépannage

### Erreur "ModuleNotFoundError"
- Vérifier que `PYTHONPATH` est correctement configuré
- Utiliser les scripts `run_tests.py` qui configurent automatiquement le PYTHONPATH

### Erreur "pytest not found"
- Installer pytest : `pip install pytest pytest-asyncio`

### Erreur de base de données
- Les tests utilisent SQLite en mémoire, normalement aucun problème
- Vérifier que SQLAlchemy est installé
