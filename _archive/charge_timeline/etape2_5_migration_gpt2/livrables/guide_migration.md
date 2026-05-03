# Guide de migration – Étape 2.5

## Vue d'ensemble

Ce guide décrit le processus de migration de LIA vers GPT-2 Small, étape par étape.

## Prérequis

- ✅ Étape 1 complétée (memory_service opérationnel)
- ✅ Étape 2 complétée (simulation_service opérationnel)
- ✅ Python 3.11+
- ✅ 2 GB RAM minimum (4 GB recommandé)
- ✅ 500 MB espace disque

## Installation

### 1. Dépendances Python

```bash
pip install transformers>=4.35.0
pip install torch>=2.0.0
pip install bitsandbytes>=0.41.0  # Pour quantisation
pip install accelerate>=0.24.0
```

### 2. Téléchargement modèle

Le modèle GPT-2 Small sera téléchargé automatiquement au premier chargement (~500 MB).

Pour pré-télécharger :

```python
from transformers import GPT2LMHeadModel, GPT2Tokenizer

model = GPT2LMHeadModel.from_pretrained("gpt2")
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
```

## Migration progressive

### Phase 1 : Installation et tests (Jour 1)

**Objectif** : Créer `LocalLLMAdapter` et le tester en parallèle des APIs externes.

**Étapes** :
1. Créer classe `LocalLLMAdapter`
2. Implémenter chargement modèle
3. Implémenter génération réponse (sans contexte)
4. Tests unitaires basiques
5. Tests de performance (latence, mémoire)

**Validation** :
- ✅ Modèle chargé sans erreur
- ✅ Réponses générées
- ✅ Latence < 5 secondes
- ✅ Mémoire < 200 MB

### Phase 2 : Intégration mémoire (Jour 2 matin)

**Objectif** : Intégrer le contexte mémoire dans le prompt.

**Étapes** :
1. Implémenter `build_prompt(context, message)`
2. Récupérer contexte depuis memory_service
3. Formater traits, souvenirs, objectifs
4. Tests d'intégration avec mémoire
5. Validation qualité des réponses

**Validation** :
- ✅ Prompt contient contexte mémoire
- ✅ Réponses cohérentes avec personnalité
- ✅ Limite tokens respectée (512 max)

### Phase 3 : Optimisation (Jour 2 après-midi)

**Objectif** : Optimiser le modèle (quantisation, cache).

**Étapes** :
1. Implémenter quantisation INT4
2. Implémenter cache du modèle
3. Tests de performance
4. Comparaison INT4 vs INT8 vs FP32

**Validation** :
- ✅ Quantisation INT4 fonctionne
- ✅ Mémoire < 200 MB
- ✅ Qualité acceptable (dégradation < 10%)

### Phase 4 : Fallback et tests finaux (Jour 3)

**Objectif** : Implémenter fallback et finaliser.

**Étapes** :
1. Implémenter fallback vers API externe
2. Tests de fallback (simulation erreurs)
3. Tests d'intégration complets
4. Documentation complète
5. Validation finale

**Validation** :
- ✅ Fallback fonctionne
- ✅ Tous les tests passent
- ✅ Documentation complète

## Configuration

### Variables d'environnement

Créer fichier `.env` :

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

### Fichier de configuration

Créer `config/local_llm.yaml` :

```yaml
local_llm:
  model_name: "gpt2"
  quantize: true
  quantization_bits: 4  # INT4
  device: "auto"
  max_memory_mb: 200
  cache_dir: "./models"
  fallback:
    enabled: true
    provider: "openai"
    api_key_env: "OPENAI_API_KEY"
```

## Utilisation

### Code de base

```python
from simulation_service.adapters import LocalLLMAdapter
from memory_service.schemas import MemoryContext

# Créer adapter
adapter = LocalLLMAdapter(
    model_name="gpt2",
    quantize=True,
    device="auto",
    fallback_adapter=external_adapter  # Optionnel
)

# Récupérer contexte mémoire
context = await memory_service.get_context(session_id="demo")

# Générer réponse
response = await adapter.send_message(
    message="Bonjour, comment vas-tu ?",
    context=context,
    max_tokens=150,
    temperature=0.7
)
```

### Intégration dans simulation_service

```python
# Dans simulation_service/orchestrator.py
from simulation_service.adapters import LocalLLMAdapter

class SimulationOrchestrator:
    def __init__(self):
        self.llm_adapter = LocalLLMAdapter()
    
    async def generate_response(self, agent_id, message, context):
        return await self.llm_adapter.send_message(
            message=message,
            context=context
        )
```

## Troubleshooting

### Erreur : OutOfMemoryError

**Cause** : Modèle trop gros pour la RAM disponible.

**Solution** :
1. Réduire quantisation (INT4 → INT8 si nécessaire)
2. Décharger autres processus
3. Utiliser GPU si disponible
4. Activer fallback automatique

### Erreur : ModelNotFoundError

**Cause** : Modèle non téléchargé.

**Solution** :
1. Vérifier connexion internet (premier téléchargement)
2. Télécharger manuellement :
   ```python
   from transformers import GPT2LMHeadModel
   model = GPT2LMHeadModel.from_pretrained("gpt2")
   ```

### Erreur : TimeoutError

**Cause** : Génération trop lente.

**Solution** :
1. Réduire `max_tokens`
2. Utiliser GPU si disponible
3. Activer fallback automatique

### Latence élevée

**Cause** : CPU lent ou modèle non optimisé.

**Solution** :
1. Vérifier quantisation (INT4 activé)
2. Utiliser GPU si disponible
3. Réduire `max_tokens`
4. Activer cache du modèle

## Comparaison avant/après

| Aspect | Avant (API externe) | Après (GPT-2 Local) |
| --- | --- | --- |
| **Coût** | ~$0.01 par 1k tokens | Gratuit |
| **Latence** | 1-3 secondes | 1-2 secondes (CPU) |
| **Dépendance** | Internet requis | 100% local |
| **Contrôle** | Limitée | Total |
| **Qualité** | Excellente | Bonne (acceptable) |
| **Mémoire** | N/A | ~200 MB |

## Prochaines étapes

Après migration réussie :

1. **Fine-tuning** (optionnel) : Fine-tuner GPT-2 sur personnalité LIA
2. **Optimisation** : Améliorer latence (GPU, cache avancé)
3. **Monitoring** : Suivre métriques (latence, qualité, erreurs)

## Support

En cas de problème :
1. Consulter section Troubleshooting
2. Vérifier logs (`logs/local_llm.log`)
3. Tester avec modèle plus petit (distilgpt2)
4. Activer fallback temporairement


