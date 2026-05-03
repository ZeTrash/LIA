# Rapport d'écarts : Code vs Livrables – Étape 2

**Date** : 2024-12-07  
**Objectif** : Vérifier la correspondance entre le code implémenté et les livrables documentaires.

---

## 🔴 RÉSUMÉ EXÉCUTIF

**Statut global** : ❌ **AUCUN CODE IMPLÉMENTÉ**

**Aucun code n'existe encore** pour l'Étape 2. Le dossier `simulation_service/` n'est pas présent dans le projet.

**Score de conformité** : **0%** (0% de code implémenté vs 100% de livrables documentaires)

---

## ❌ CODE MANQUANT PAR SOUS-LOT

### SL1 – Protocole de communication

**Livrables documentaires** :
- ✅ `protocol_message_schema.json` : JSON Schema complet
- ✅ `protocol_handshake_schema.json` : Schéma handshake
- ✅ Documentation protocole dans README

**Code attendu** :
- ❌ Module de validation des messages (validation JSON Schema)
- ❌ Fonctions de sérialisation/désérialisation
- ❌ Gestion des sessions multi-agents
- ❌ Implémentation du handshake
- ❌ Types Python pour les messages (Pydantic models)

**Fichiers manquants** :
- `simulation_service/src/simulation_service/protocol.py`
- `simulation_service/src/simulation_service/schemas.py` (partie protocole)

---

### SL2 – Service de simulation

**Livrables documentaires** :
- ✅ `api_spec_simulation.yaml` : OpenAPI 3.1 avec 5 endpoints
- ✅ `architecture_technique.md` : Architecture complète

**Code attendu** :
- ❌ Service FastAPI (`api.py`)
- ❌ Orchestrator (`orchestrator.py`)
- ❌ Agent Adapters (`adapters.py`)
- ❌ Session Manager (`session.py`)
- ❌ Configuration (`config.py`)
- ❌ Point d'entrée (`main.py`)

**Endpoints manquants** :
- ❌ `POST /simulation/start`
- ❌ `POST /simulation/{session_id}/message`
- ❌ `GET /simulation/{session_id}/status`
- ❌ `POST /simulation/{session_id}/stop`
- ❌ `GET /simulation/{session_id}/export`

**Composants manquants** :
- ❌ Classe `SimulationOrchestrator`
- ❌ Interface `AgentAdapter` (ABC)
- ❌ Implémentations : `LIAAdapter`, `ExternalLLMAdapter`, `SimulatedAgentAdapter`
- ❌ Classe `SessionManager`
- ❌ Classe `SimulationSession`

**Fichiers manquants** :
- `simulation_service/src/simulation_service/api.py`
- `simulation_service/src/simulation_service/orchestrator.py`
- `simulation_service/src/simulation_service/adapters.py`
- `simulation_service/src/simulation_service/session.py`
- `simulation_service/src/simulation_service/config.py`
- `simulation_service/src/simulation_service/main.py`
- `simulation_service/src/simulation_service/__init__.py`

---

### SL3 – Capture et métriques

**Livrables documentaires** :
- ✅ `algorithmes_metriques.md` : Formules et pseudo-code complets

**Code attendu** :
- ❌ Module `metrics_calculator.py`
- ❌ Fonctions de calcul :
  - ❌ `calculate_variability()`
  - ❌ `calculate_autonomy()`
  - ❌ `calculate_curiosity()`
  - ❌ `calculate_coherence()`
- ❌ Intégration avec memory_service (journalisation)
- ❌ Format d'export JSON

**Fichiers manquants** :
- `simulation_service/src/simulation_service/metrics.py`
- `simulation_service/src/simulation_service/memory_integration.py`

**Fonctionnalités manquantes** :
- ❌ Création d'`Experience` dans memory_service
- ❌ Enrichissement des `InteractionLog` avec métadonnées multi-agent
- ❌ Calcul des métriques en temps réel
- ❌ Calcul des métriques en batch (fin de simulation)
- ❌ Export JSON des résultats

---

### SL4 – Interface de supervision

**Livrables documentaires** :
- ✅ `plan_tests_validation.md` : Plan de tests complet
- ✅ Documentation CLI dans README

**Code attendu** :
- ❌ CLI (`cli.py`)
- ❌ Dashboard terminal
- ❌ Visualisation des échanges
- ❌ Scripts de lancement

**Commandes CLI manquantes** :
- ❌ `lia-sim start`
- ❌ `lia-sim status`
- ❌ `lia-sim stop`
- ❌ `lia-sim export`

**Fichiers manquants** :
- `simulation_service/src/simulation_service/cli.py`
- `simulation_service/src/simulation_service/dashboard.py`

---

## 📊 TABLEAU RÉCAPITULATIF DES ÉCARTS

| Composant | Livrable documentaire | Code attendu | Code présent | Écart |
|-----------|----------------------|--------------|--------------|-------|
| **SL1 - Protocole** | JSON Schema messages | Validation, sérialisation | ❌ Absent | 🔴 100% manquant |
| **SL1 - Protocole** | JSON Schema handshake | Implémentation handshake | ❌ Absent | 🔴 100% manquant |
| **SL2 - API** | OpenAPI 5 endpoints | Service FastAPI | ❌ Absent | 🔴 100% manquant |
| **SL2 - Orchestrator** | Architecture | Classe Orchestrator | ❌ Absent | 🔴 100% manquant |
| **SL2 - Adapters** | Architecture | 3 adapters (LIA, External, Simulated) | ❌ Absent | 🔴 100% manquant |
| **SL2 - Session** | Architecture | SessionManager | ❌ Absent | 🔴 100% manquant |
| **SL3 - Métriques** | Algorithmes | 4 fonctions de calcul | ❌ Absent | 🔴 100% manquant |
| **SL3 - Journalisation** | Architecture | Intégration memory_service | ❌ Absent | 🔴 100% manquant |
| **SL4 - CLI** | Documentation | CLI avec 4 commandes | ❌ Absent | 🔴 100% manquant |
| **SL4 - Dashboard** | Documentation | Dashboard terminal | ❌ Absent | 🔴 100% manquant |

**Score global** : **0%** (0/10 composants implémentés)

---

## 📋 STRUCTURE DE CODE ATTENDUE

### Structure de dossiers manquante

```
simulation_service/
├── README.md
├── requirements.txt
├── src/
│   └── simulation_service/
│       ├── __init__.py
│       ├── api.py              # FastAPI endpoints
│       ├── orchestrator.py     # SimulationOrchestrator
│       ├── adapters.py          # AgentAdapter, LIAAdapter, etc.
│       ├── session.py           # SessionManager, SimulationSession
│       ├── metrics.py           # MetricsCalculator
│       ├── schemas.py           # Pydantic models
│       ├── config.py            # Configuration
│       ├── cli.py               # CLI interface
│       ├── dashboard.py         # Dashboard terminal
│       └── main.py              # Point d'entrée
├── tests/
│   ├── test_api.py
│   ├── test_orchestrator.py
│   ├── test_adapters.py
│   ├── test_metrics.py
│   └── test_integration.py
└── data/
    └── scenarios.json           # Scénarios prédéfinis
```

---

## 🔍 DÉTAIL DES ÉCARTS PAR COMPOSANT

### 1. Protocole de communication (SL1)

#### Validation JSON Schema

**Attendu** :
```python
from jsonschema import validate
from .schemas import MessageSchema, HandshakeSchema

def validate_message(message: dict) -> bool:
    validate(instance=message, schema=MessageSchema)
    return True
```

**Présent** : ❌ Absent

#### Sérialisation/Désérialisation

**Attendu** :
```python
def serialize_message(message: MultiAgentMessage) -> str:
    return json.dumps(message.model_dump())

def deserialize_message(data: str) -> MultiAgentMessage:
    return MultiAgentMessage.model_validate_json(data)
```

**Présent** : ❌ Absent

#### Handshake

**Attendu** :
```python
async def perform_handshake(agent_config: AgentConfig) -> HandshakeResponse:
    # Échange de métadonnées entre agents
    pass
```

**Présent** : ❌ Absent

---

### 2. Service de simulation (SL2)

#### Endpoints FastAPI

**Attendu** (selon `api_spec_simulation.yaml`) :
```python
@app.post("/simulation/start")
async def start_simulation(request: SimulationStartRequest):
    # Créer session, initialiser agents, handshake
    pass

@app.post("/simulation/{session_id}/message")
async def send_message(session_id: str, request: MessageRequest):
    # Orchestrer l'échange, journaliser
    pass

@app.get("/simulation/{session_id}/status")
async def get_status(session_id: str):
    # Retourner statut, métriques
    pass

@app.post("/simulation/{session_id}/stop")
async def stop_simulation(session_id: str):
    # Finaliser, exporter
    pass

@app.get("/simulation/{session_id}/export")
async def export_simulation(session_id: str, format: str = "json"):
    # Exporter résultats
    pass
```

**Présent** : ❌ Absent (aucun endpoint)

#### Orchestrator

**Attendu** (selon `architecture_technique.md`) :
```python
class SimulationOrchestrator:
    def __init__(self):
        self.sessions: Dict[str, SimulationSession] = {}
    
    async def start_simulation(self, config: SimulationConfig) -> str:
        # Créer session, initialiser agents
        pass
    
    async def process_message(self, session_id: str, message: Message) -> Message:
        # Rotation agents, appel adapters, gouvernance
        pass
    
    def detect_loop(self, session_id: str) -> bool:
        # Détection boucle (3 messages identiques)
        pass
```

**Présent** : ❌ Absent

#### Agent Adapters

**Attendu** :
```python
from abc import ABC, abstractmethod

class AgentAdapter(ABC):
    @abstractmethod
    async def send_message(self, message: str, context: dict) -> str:
        pass

class LIAAdapter(AgentAdapter):
    async def send_message(self, message: str, context: dict) -> str:
        # GET /context, appel LLM, POST /governance/check
        pass

class ExternalLLMAdapter(AgentAdapter):
    async def send_message(self, message: str, context: dict) -> str:
        # Appel API OpenAI/Anthropic avec retry
        pass

class SimulatedAgentAdapter(AgentAdapter):
    async def send_message(self, message: str, context: dict) -> str:
        # Logique prédéfinie
        pass
```

**Présent** : ❌ Absent

#### Session Manager

**Attendu** :
```python
class SimulationSession:
    session_id: str
    agents: List[AgentConfig]
    messages: List[Message]
    status: str
    current_turn: int
    metrics: BehavioralMetrics

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SimulationSession] = {}
    
    def create_session(self, config: SimulationConfig) -> SimulationSession:
        pass
    
    def get_session(self, session_id: str) -> SimulationSession:
        pass
```

**Présent** : ❌ Absent

---

### 3. Capture et métriques (SL3)

#### Metrics Calculator

**Attendu** (selon `algorithmes_metriques.md`) :
```python
def calculate_variability(messages: List[Message]) -> float:
    # Entropie de Shannon + diversité sujets
    entropy = calculate_entropy(messages)
    diversity = calculate_topic_diversity(messages)
    return entropy * 0.6 + diversity * 0.4

def calculate_autonomy(messages: List[Message], agent_id: str) -> float:
    # Messages initiés + questions
    initiated_ratio = count_initiated(messages, agent_id) / len(messages)
    questions_ratio = count_questions(messages, agent_id) / len(messages)
    return initiated_ratio * 0.6 + questions_ratio * 0.4

def calculate_curiosity(messages: List[Message], agent_id: str) -> float:
    # Questions + exploration nouveaux sujets
    questions_ratio = count_questions(messages, agent_id) / len(messages)
    exploration_ratio = calculate_exploration(messages, agent_id)
    return questions_ratio * 0.5 + exploration_ratio * 0.5

def calculate_coherence(messages: List[Message], agent_id: str, initial_traits: dict) -> float:
    # Score gouvernance + stabilité traits
    mean_coherence = mean([msg.metadata.scores.coherence for msg in messages])
    trait_drift = calculate_trait_drift(initial_traits, get_final_traits(agent_id))
    return mean_coherence * 0.7 + (1 - trait_drift) * 0.3
```

**Présent** : ❌ Absent

#### Intégration memory_service

**Attendu** :
```python
async def log_simulation_interaction(session_id: str, message: Message, response: Message):
    # POST /interaction avec métadonnées multi-agent
    interaction_request = InteractionRequest(
        session_id=session_id,
        prompt=message.content,
        response=response.content,
        metadata={
            "simulation_type": "multi-agent",
            "agent_partner_id": response.agent_id,
            "turn": message.metadata.turn
        }
    )
    await memory_service.post_interaction(interaction_request)

async def create_simulation_experience(session_id: str, metrics: BehavioralMetrics):
    # Créer Experience dans memory_service
    experience = Experience(
        experience_id=f"exp-sim-{session_id}",
        title=f"Simulation multi-agent {session_id}",
        metrics_snapshot=metrics.model_dump()
    )
    await memory_service.create_experience(experience)
```

**Présent** : ❌ Absent

---

### 4. Interface de supervision (SL4)

#### CLI

**Attendu** :
```python
import click

@click.group()
def cli():
    """LIA Simulation Multi-Agent CLI"""
    pass

@cli.command()
@click.option('--agent1', required=True)
@click.option('--agent2', required=True)
@click.option('--max-turns', default=50)
def start(agent1, agent2, max_turns):
    """Démarrer une simulation"""
    # POST /simulation/start
    pass

@cli.command()
@click.argument('session_id')
def status(session_id):
    """Voir le statut d'une simulation"""
    # GET /simulation/{session_id}/status
    pass

@cli.command()
@click.argument('session_id')
def stop(session_id):
    """Arrêter une simulation"""
    # POST /simulation/{session_id}/stop
    pass

@cli.command()
@click.argument('session_id')
@click.option('--format', default='json')
def export(session_id, format):
    """Exporter les résultats"""
    # GET /simulation/{session_id}/export
    pass
```

**Présent** : ❌ Absent

#### Dashboard terminal

**Attendu** :
```python
from rich.console import Console
from rich.table import Table
from rich.live import Live

def display_dashboard(session_id: str):
    console = Console()
    # Affichage en temps réel des métriques
    # Tableau des messages
    # Barres de progression
    pass
```

**Présent** : ❌ Absent

---

## 📊 RÉSUMÉ QUANTITATIF

| Catégorie | Livrables documentaires | Code attendu | Code présent | Écart |
|-----------|------------------------|--------------|--------------|-------|
| **Protocole** | 100% | 100% | 0% | 🔴 -100% |
| **Service API** | 100% | 100% | 0% | 🔴 -100% |
| **Orchestration** | 100% | 100% | 0% | 🔴 -100% |
| **Métriques** | 100% | 100% | 0% | 🔴 -100% |
| **Supervision** | 100% | 100% | 0% | 🔴 -100% |

**Score global de conformité** : **0%**  
**Blocage fonctionnel** : ✅ **OUI** (aucun code = aucune fonctionnalité)  
**Blocage architectural** : ✅ **OUI** (structure complète à créer)

---

## ✅ CONCLUSION

**Situation actuelle** : Aucun code n'a été implémenté pour l'Étape 2.

**Livrables documentaires** : ✅ **100% complets et validés**  
**Code implémenté** : ❌ **0%** (aucun code)

**Recommandation** : Démarrer l'implémentation en suivant les spécifications documentaires. Les livrables sont suffisamment détaillés pour guider l'implémentation complète.

---

## 🎯 PLAN D'IMPLÉMENTATION SUGGÉRÉ

### Phase 1 : Structure de base (0,5 j)
1. Créer structure de dossiers `simulation_service/`
2. Créer `requirements.txt` (FastAPI, httpx, pydantic, jsonschema, rich)
3. Créer `__init__.py` et modules de base

### Phase 2 : Protocole (SL1) - 0,5 j
1. Implémenter validation JSON Schema
2. Créer schémas Pydantic (`schemas.py`)
3. Implémenter handshake

### Phase 3 : Service simulation (SL2) - 2 j
1. Créer `config.py`
2. Implémenter `SessionManager` et `SimulationSession`
3. Implémenter `AgentAdapter` et 3 adapters
4. Implémenter `SimulationOrchestrator`
5. Créer endpoints FastAPI (`api.py`)
6. Créer `main.py`

### Phase 4 : Métriques (SL3) - 1,5 j
1. Implémenter `metrics_calculator.py` (4 fonctions)
2. Implémenter intégration memory_service
3. Implémenter export JSON

### Phase 5 : Supervision (SL4) - 1 j
1. Implémenter CLI (`cli.py`)
2. Implémenter dashboard terminal (`dashboard.py`)
3. Tests et documentation

**Durée totale estimée** : **5,5 jours** (selon cahier des charges)

