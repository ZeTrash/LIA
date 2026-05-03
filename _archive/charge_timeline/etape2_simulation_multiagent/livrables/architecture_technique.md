# Architecture technique – Service de simulation multi-agent

## Vue d'ensemble

Le service de simulation multi-agent orchestre les conversations entre LIA et d'autres agents (LIA, LLM externes, agents simulés) et journalise les interactions dans la mémoire locale.

## Architecture système

```
┌─────────────────────────────────────────┐
│     Simulation Service (FastAPI)         │
│  ┌───────────────────────────────────┐  │
│  │  Orchestrator                     │  │
│  │  - Gestion sessions               │  │
│  │  - Rotation agents                │  │
│  │  - Détection boucles/timeouts     │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Metrics Calculator               │  │
│  │  - Variabilité, Autonomie         │  │
│  │  - Curiosité, Cohérence            │  │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────────┐
│ Memory  │         │ LLM Provider │
│ Service │         │ (OpenAI/etc) │
│ (Étape1)│         └──────────────┘
└─────────┘
```

## Composants principaux

### 1. Orchestrator

**Responsabilités** :
- Gestion des sessions de simulation
- Rotation des agents (round-robin ou configuré)
- Détection de boucles d'erreur
- Gestion des timeouts
- Intégration avec memory_service

**Implémentation** :
- Classe `SimulationOrchestrator`
- État des sessions en mémoire (dict) + persistance optionnelle
- Thread pool pour appels asynchrones aux agents

### 2. Agent Adapters

**Types d'agents supportés** :

#### LIA Primary/Secondary
- Utilise `GET /context` pour récupérer contexte mémoire
- Utilise LLM local ou API interne
- Applique gouvernance via `POST /governance/check`

#### LLM Externe
- Adapter pour OpenAI, Anthropic, etc.
- Gestion des clés API, rate limiting
- Retry avec backoff exponentiel

#### Agent Simulé
- Logique prédéfinie (règles, templates)
- Utile pour tests et validation

**Implémentation** :
- Interface `AgentAdapter` (ABC)
- Implémentations : `LIAAdapter`, `ExternalLLMAdapter`, `SimulatedAgentAdapter`

### 3. Metrics Calculator

**Responsabilités** :
- Calcul des métriques comportementales
- Agrégation par session/agent
- Export des résultats

**Implémentation** :
- Module `metrics_calculator.py`
- Fonctions : `calculate_variability()`, `calculate_autonomy()`, etc.
- Cache pour calculs incrémentaux

### 4. Session Manager

**Responsabilités** :
- Création/suppression de sessions
- Stockage des messages en mémoire
- Persistance optionnelle (SQLite ou JSON)

**Implémentation** :
- Classe `SessionManager`
- Stockage : `Dict[str, SimulationSession]`
- Nettoyage automatique des sessions expirées

## Flux d'exécution

### Démarrage d'une simulation

```
1. POST /simulation/start
   ↓
2. Créer SimulationSession
   ↓
3. Initialiser agents (handshake)
   ↓
4. Créer Experience dans memory_service
   ↓
5. Retourner session_id
```

### Envoi d'un message

```
1. POST /simulation/{session_id}/message
   ↓
2. Récupérer session
   ↓
3. Déterminer agent suivant (rotation)
   ↓
4. Si LIA : GET /context (memory_service)
   ↓
5. Appeler agent (LLM ou simulé)
   ↓
6. POST /governance/check (memory_service)
   ↓
7. Si verdict != block :
     - POST /interaction (memory_service)
     - Calculer métriques incrémentales
     - Passer au tour suivant
   Sinon :
     - Arrêter simulation (stopped_drift)
```

### Arrêt d'une simulation

```
1. POST /simulation/{session_id}/stop
   ↓
2. Calculer métriques finales
   ↓
3. Finaliser Experience dans memory_service
   ↓
4. Exporter résultats
   ↓
5. Nettoyer session
```

## Gestion des erreurs

### Timeout

- **Détection** : Timer par message (30s par défaut)
- **Action** : Marquer tour comme timeout, continuer ou arrêter après 3 timeouts consécutifs

### Boucle d'erreur

- **Détection** : Hash SHA-256 des 3 derniers messages identiques
- **Action** : Arrêter simulation avec statut `stopped_loop`

### Dérive

- **Détection** : `POST /governance/check` retourne `verdict: block`
- **Action** : Arrêter simulation avec statut `stopped_drift`, créer `Souvenir` alert

### Agent indisponible

- **Détection** : Erreur réseau persistante (3 retries échoués)
- **Action** : Marquer agent comme `unavailable`, exclure des tours suivants

## Stockage et persistance

### En mémoire

- Sessions actives : `Dict[str, SimulationSession]`
- Messages : Stockés dans la session jusqu'à finalisation

### Persistance

- **Memory Service** : `InteractionLog`, `Experience`, `Souvenir`
- **Export JSON** : Résultats complets exportés à la fin

## Performance

### Optimisations

- **Calcul métriques** : Batch à la fin (précis) + approximation temps réel (dashboard)
- **Cache contexte** : Contexte mémoire mis en cache pour 5 secondes
- **Pool de threads** : Appels asynchrones aux agents externes

### Limites

- **Sessions simultanées** : 10 par défaut (configurable)
- **Tours max** : 50 par défaut (configurable)
- **Timeout** : 30 secondes par message (configurable)

## Sécurité

- **Authentification** : Token API (`X-LIA-Token`) pour endpoints
- **Validation** : JSON Schema pour tous les messages
- **Rate limiting** : 10 messages/seconde par agent (configurable)
- **Isolation** : Chaque session isolée (pas de fuite de données)

## Dépendances

- **FastAPI** : Framework web
- **httpx** : Client HTTP asynchrone (agents externes)
- **pydantic** : Validation des données
- **memory_service** : Service mémoire (Étape 1)
- **sqlalchemy** : Optionnel (persistance sessions)

## Configuration

```python
class SimulationConfig:
    max_sessions: int = 10
    max_turns: int = 50
    timeout_seconds: int = 30
    max_concurrent_requests: int = 5
    rate_limit_per_agent: int = 10  # messages/seconde
    enable_metrics_realtime: bool = True
    enable_persistence: bool = False  # Optionnel
```

## Déploiement

- **Local** : `uvicorn simulation_service.main:app --port 4700`
- **Docker** : Image avec FastAPI + dépendances
- **Production** : Gunicorn + plusieurs workers (si nécessaire)




