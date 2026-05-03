# Architecture technique – Migration GPT-2 Small

## Vue d'ensemble

Migration de LIA vers un modèle LLM local (GPT-2 Small) pour éliminer les dépendances externes et obtenir un contrôle total sur la personnalité.

## Architecture système

```
┌─────────────────────────────────────────┐
│         LIA Core                        │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐                   │
│  │ LocalLLMAdapter  │                   │
│  │ (GPT-2 Small)    │                   │
│  │                  │                   │
│  │  ┌────────────┐  │                   │
│  │  │ GPT-2      │  │                   │
│  │  │ (124M)     │  │                   │
│  │  │ INT4       │  │                   │
│  │  │ 125 MB     │  │                   │
│  │  └────────────┘  │                   │
│  └────────┬─────────┘                   │
│           │                              │
│           │ build_prompt(context, msg)   │
│           │                              │
│           ▼                              │
│  ┌──────────────────┐                   │
│  │  Memory Service  │                   │
│  │  (GET /context)  │                   │
│  └──────────────────┘                   │
│                                         │
│  ┌──────────────────┐ (fallback)       │
│  │ External Adapter │                   │
│  │ (OpenAI/Gemini)  │                   │
│  └──────────────────┘                   │
└─────────────────────────────────────────┘
```

## Composants principaux

### 1. LocalLLMAdapter

**Responsabilités** :
- Chargement GPT-2 Small via transformers
- Quantisation INT4/INT8
- Construction prompt avec contexte mémoire
- Génération de réponses
- Gestion cache modèle
- Fallback vers API externe

**Implémentation** :
- Classe `LocalLLMAdapter` dans `simulation_service/src/simulation_service/adapters.py`
- Dépendances : `transformers`, `torch`, `bitsandbytes` (quantisation)

### 2. Prompt Builder

**Responsabilités** :
- Récupérer contexte depuis memory_service (`GET /context`)
- Formater traits, souvenirs, objectifs en prompt
- Gérer limite de tokens (512 max)

**Implémentation** :
- Méthode `build_prompt()` dans `LocalLLMAdapter`
- Format structuré avec sections claires

### 3. Model Manager

**Responsabilités** :
- Chargement/déchargement du modèle
- Gestion mémoire (limite 200 MB)
- Cache du modèle en mémoire
- Détection GPU (CUDA)

**Implémentation** :
- Méthodes `load_model()`, `unload_model()`
- Singleton pattern pour cache

### 4. Fallback Handler

**Responsabilités** :
- Détection d'erreurs (timeout, OOM, etc.)
- Basculement automatique vers API externe
- Logging des erreurs

**Implémentation** :
- Try/except dans `send_message()`
- Configuration fallback_adapter

## Flux d'exécution

### Génération d'une réponse

```
1. LIA Core appelle LocalLLMAdapter.send_message()
   ↓
2. Récupérer contexte mémoire (GET /context)
   ↓
3. Construire prompt (build_prompt())
   ↓
4. Charger modèle si nécessaire (cache)
   ↓
5. Générer réponse avec GPT-2 Small
   ↓
6. Si erreur → Fallback vers API externe
   ↓
7. Retourner réponse
   ↓
8. Journaliser interaction (POST /interaction)
```

### Chargement du modèle

```
1. Premier appel → load_model()
   ↓
2. Télécharger GPT-2 Small (si pas en cache)
   ↓
3. Appliquer quantisation INT4
   ↓
4. Charger en mémoire
   ↓
5. Mettre en cache (singleton)
```

## Optimisations

### Quantisation

- **INT4** : ~125 MB, ~150-200 MB RAM
- **INT8** : ~250 MB, ~300-400 MB RAM
- **FP32** : ~500 MB, ~600 MB RAM (non recommandé)

### Cache

- Modèle chargé une seule fois (singleton)
- Reste en mémoire jusqu'à arrêt
- Déchargement manuel si nécessaire

### GPU

- Détection automatique CUDA
- Utilisation si disponible (accélération)
- Fallback CPU si pas de GPU

## Gestion des erreurs

### OutOfMemoryError

- **Détection** : Exception lors du chargement
- **Action** : Décharger modèle, réduire quantisation, fallback API

### TimeoutError

- **Détection** : Génération > 30 secondes
- **Action** : Annuler génération, fallback API

### ModelNotFoundError

- **Détection** : Modèle non téléchargé
- **Action** : Téléchargement automatique via transformers

## Migration progressive

### Phase 1 : Parallèle

- LocalLLMAdapter créé et testé
- APIs externes toujours utilisées
- Tests de comparaison

### Phase 2 : Mixte (50/50)

- 50% des requêtes → LocalLLMAdapter
- 50% des requêtes → API externe
- Monitoring qualité

### Phase 3 : Local avec fallback

- 100% des requêtes → LocalLLMAdapter
- Fallback API si erreur
- Logging des fallbacks

### Phase 4 : Fine-tuning (optionnel)

- Fine-tuning GPT-2 sur personnalité LIA
- Amélioration qualité des réponses

## Dépendances

### Python

```txt
transformers>=4.35.0
torch>=2.0.0
bitsandbytes>=0.41.0  # Pour quantisation
accelerate>=0.24.0
```

### Système

- **RAM** : Minimum 2 GB (recommandé 4 GB)
- **Disque** : ~500 MB pour modèle + cache
- **CPU** : Tout processeur moderne (GPU optionnel)

## Configuration

### Fichier `.env`

```bash
# Local LLM
LIA_LOCAL_LLM_MODEL=gpt2
LIA_LOCAL_LLM_QUANTIZE=true
LIA_LOCAL_LLM_DEVICE=auto
LIA_LOCAL_LLM_MAX_MEMORY_MB=200
LIA_LOCAL_LLM_CACHE_DIR=./models
LIA_LOCAL_LLM_FALLBACK_ENABLED=true
LIA_LOCAL_LLM_FALLBACK_PROVIDER=openai
```

### Fichier `config.yaml`

```yaml
local_llm:
  model_name: "gpt2"
  quantize: true
  quantization_bits: 4  # INT4
  device: "auto"  # cpu, cuda, auto
  max_memory_mb: 200
  cache_dir: "./models"
  fallback:
    enabled: true
    provider: "openai"  # openai, gemini
    api_key_env: "OPENAI_API_KEY"
```

## Performance

### Métriques cibles

| Métrique | Cible | Mesure |
| --- | --- | --- |
| Latence | < 2s | Temps génération réponse |
| Mémoire | < 200 MB | RAM utilisée (quantisé) |
| Qualité | Cohérent | Cohérence avec personnalité |
| Taux erreur | < 5% | Erreurs nécessitant fallback |

### Optimisations possibles

- **Batch processing** : Traiter plusieurs messages ensemble
- **Streaming** : Génération token par token (UX)
- **Cache prompts** : Mettre en cache prompts similaires
- **GPU** : Accélération si CUDA disponible

## Sécurité

- **Modèle local** : Pas de données envoyées à l'extérieur
- **Cache** : Stockage local uniquement
- **Fallback** : API externe seulement si erreur (optionnel)

## Déploiement

### Local

```bash
# Installation
pip install transformers torch bitsandbytes

# Utilisation
python -m simulation_service.main
```

### Docker

```dockerfile
FROM python:3.11-slim

RUN pip install transformers torch bitsandbytes

COPY . /app
WORKDIR /app

CMD ["python", "-m", "simulation_service.main"]
```

### Production

- Modèle pré-téléchargé dans l'image
- Cache persistant (volume)
- Monitoring mémoire et latence


