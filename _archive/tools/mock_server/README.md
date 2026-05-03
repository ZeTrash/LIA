# Mock server LIA mémoire

Serveur FastAPI léger qui charge la spécification `api_spec_openapi.yaml` et sert des réponses de démonstration pour les endpoints clés. Utile pour valider les intégrations côté LLM sans démarrer le service complet.

## Installation

```bash
cd tools/mock_server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
# Depuis la racine du projet LIA
cd tools/mock_server
.venv\Scripts\python.exe -m mock_server.server
# ou
uvicorn mock_server.server:app --port 4600
```

Endpoints disponibles :
- `GET /context?session_id=demo` – renvoie le paquet JSON d'exemple.
- `POST /interaction` – renvoie un log simulé.
- `POST /trait-update` – simule une mise à jour.
- `POST /governance/check` – verdict basé sur `signals.drift_score` si fourni.
- `GET /metrics` – renvoie un set de KPI mock.
- `GET /openapi.yaml` – renvoie la spec utilisée.

Le serveur lit directement `../../charge_timeline/etape1_cahier_charges/livrables/api_spec_openapi.yaml`, toute mise à jour sera visible sans changer le code.




