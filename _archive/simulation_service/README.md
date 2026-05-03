# Simulation Service – Étape 2

Service FastAPI pour orchestrer des simulations multi-agents permettant à LIA de discuter avec d'autres agents (LIA, LLM externes, agents simulés).

## Structure

```
simulation_service/
├── requirements.txt
├── src/simulation_service/
│   ├── __init__.py
│   ├── api.py              # Endpoints FastAPI
│   ├── orchestrator.py     # SimulationOrchestrator
│   ├── adapters.py          # AgentAdapter, LIAAdapter, etc.
│   ├── session.py           # SessionManager, SimulationSession
│   ├── metrics.py           # MetricsCalculator
│   ├── schemas.py           # Pydantic models
│   ├── protocol.py          # Validation protocole, handshake
│   ├── config.py            # Configuration
│   ├── cli.py               # CLI interface
│   ├── dashboard.py         # Dashboard terminal
│   └── main.py              # Point d'entrée
├── tests/
│   ├── test_api.py
│   ├── test_orchestrator.py
│   ├── test_adapters.py
│   ├── test_metrics.py
│   └── test_integration.py
└── data/
    └── scenarios.json       # Scénarios prédéfinis
```

## Installation

```bash
cd simulation_service
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Lancer le serveur

**Option 1 - Utiliser le script wrapper (recommandé) :**
```powershell
.\start-server.ps1
# ou
.\start-server.bat
```

**Option 2 - Commande directe avec PYTHONPATH :**
```powershell
$env:PYTHONPATH = "$PWD\src"; & C:\Python313\python.exe -m simulation_service.main
```

**Option 3 - Avec uvicorn directement :**
```powershell
$env:PYTHONPATH = "$PWD\src"; & C:\Python313\python.exe -m uvicorn simulation_service.api:create_app --factory --reload --host 127.0.0.1 --port 4700
```

Le service sera accessible sur `http://127.0.0.1:4700`

## Endpoints principaux

- `POST /simulation/start` – Démarre une simulation multi-agent
- `POST /simulation/{session_id}/message` – Envoie un message dans une simulation
- `GET /simulation/{session_id}/status` – Récupère le statut d'une simulation
- `POST /simulation/{session_id}/stop` – Arrête une simulation
- `GET /simulation/{session_id}/export` – Exporte les résultats

## Configuration

Le service nécessite que `memory_service` soit en cours d'exécution (par défaut sur `http://127.0.0.1:8000`).

### Modèle LLM Local (GPT-2 Small)

Le service supporte maintenant un modèle LLM local (GPT-2 Small) pour une autonomie complète :

**Installation des dépendances** :

**Pour CPU uniquement** :
```bash
pip install transformers torch accelerate bitsandbytes psutil
```

**Pour GPU (CUDA)** :
```bash
# Python 3.13 : Utilisez les builds nightly
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121
# Ou pour CUDA 11.8 : --index-url https://download.pytorch.org/whl/nightly/cu118
# Ou pour CUDA 13.0 : --index-url https://download.pytorch.org/whl/nightly/cu130

# Python 3.11/3.12 : Builds stables disponibles
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

pip install transformers accelerate bitsandbytes psutil

# Voir SOLUTION_GPU.md pour plus de détails
```

**Vérifier que le GPU est détecté** :
```python
import torch
print("CUDA disponible:", torch.cuda.is_available())
print("Nombre de GPUs:", torch.cuda.device_count())
```

**Configuration** :
- `SIMULATION_SERVICE_LOCAL_LLM_MODEL` : Nom du modèle (défaut: `gpt2`, peut être `distilgpt2` pour plus léger)
- `SIMULATION_SERVICE_LOCAL_LLM_QUANTIZE` : Activer la quantisation (défaut: `True`)
- `SIMULATION_SERVICE_LOCAL_LLM_QUANTIZATION_BITS` : Bits de quantisation (défaut: `4` pour INT4, peut être `8` pour INT8)
- `SIMULATION_SERVICE_LOCAL_LLM_DEVICE` : Device (`auto`, `cpu`, `cuda`)

**Utilisation** :
```python
# Dans une simulation
agent_configs = [
    {"agent_id": "lia-primary", "agent_type": "lia-primary"},
    {"agent_id": "local-llm", "agent_type": "llm-local"}  # Utilise GPT-2 local
]
```

**Avantages** :
- ✅ 100% local (pas d'internet requis)
- ✅ Gratuit (pas de coûts API)
- ✅ Contrôle total sur la personnalité
- ✅ Modèle "vierge" (personnalité vient uniquement de la mémoire)

### Variables d'environnement

Les paramètres peuvent être définis via variables d'environnement (préfixe `SIMULATION_SERVICE_`) ou fichier `.env` :
- `SIMULATION_SERVICE_MEMORY_URL` : URL du service mémoire (défaut: `http://127.0.0.1:8000`)
- `SIMULATION_SERVICE_PORT` : Port du service (défaut: `4700`)
- `SIMULATION_SERVICE_OPENAI_API_KEY` : Clé API OpenAI (optionnel)
- `SIMULATION_SERVICE_ANTHROPIC_API_KEY` : Clé API Anthropic (optionnel)
- `SIMULATION_SERVICE_GEMINI_API_KEY` : Clé API Gemini (optionnel)

### Fichier api.conf

Les clés API peuvent également être définies dans `config/api.conf` à la racine du projet :
```ini
openai_api_key = YOUR_OPENAI_API_KEY
anthropic_api_key = YOUR_ANTHROPIC_API_KEY
gemini_api_key = YOUR_GEMINI_API_KEY
```

**Priorité** : Variables d'environnement > `.env` > `config/api.conf`

## Utilisation du CLI

Le CLI permet d'interagir avec le service de simulation via la ligne de commande.

**Important** : Le serveur doit être démarré avant d'utiliser le CLI.

### Commandes disponibles

**Démarrer une simulation :**
```powershell
.\lia-sim.ps1 start --agent1 agent1 --agent2 agent2 --max-turns 20
# ou
.\lia-sim.bat start --agent1 agent1 --agent2 agent2 --max-turns 20
```

**Voir le statut d'une simulation :**
```powershell
.\lia-sim.ps1 status <session_id>
```

**Envoyer un message :**
```powershell
.\lia-sim.ps1 message <session_id> --agent-id agent1 --content "Bonjour"
```

**Arrêter une simulation :**
```powershell
.\lia-sim.ps1 stop <session_id>
```

**Exporter les résultats :**
```powershell
.\lia-sim.ps1 export <session_id> --format json --output results.json
```

**Voir l'aide :**
```powershell
.\lia-sim.ps1 --help
```

**Alternative - Commande directe :**
```powershell
$env:PYTHONPATH = "$PWD\src"; & C:\Python313\python.exe -m simulation_service.cli --help
```

## Tests

```powershell
$env:PYTHONPATH = "$PWD\src"; & C:\Python313\python.exe -m pytest tests/ -v
```

## Documentation

Voir `charge_timeline/etape2_simulation_multiagent/README.md` pour la documentation complète.
