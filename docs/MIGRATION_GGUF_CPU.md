# Migration vers GGUF pour CPU-only

## Problème résolu

**Avant** : Le code utilisait `bitsandbytes` avec `load_in_4bit`, ce qui nécessite obligatoirement CUDA/GPU. Sur CPU, la quantisation échouait avec le message :
```
Quantisation INT4 nécessite CUDA (GPU non disponible)
```

**Maintenant** : Le code détecte automatiquement CPU vs GPU et utilise :
- **CPU** → GGUF + llama.cpp (100% CPU, optimisé)
- **GPU** → transformers + bitsandbytes (comme avant)

## Architecture

### Niveaux de quantification

| Niveau | GPU requis ? | Explication |
|--------|--------------|-------------|
| Quantification du modèle (pré-traitement) | ❌ Non | On peut quantifier sur CPU |
| Chargement d'un modèle déjà quantifié | ❌ Non | Fonctionne très bien sur CPU |
| Quantification dynamique avec bitsandbytes CUDA | ✅ Oui | Ancienne méthode (GPU-only) |
| **GGUF + llama.cpp** | ❌ **Non** | **Nouvelle méthode (CPU-only)** |

### Solution implémentée

**GGUF (GPT-Generated Unified Format)** est le format standard pour les modèles quantifiés CPU :
- ✅ Fonctionne 100% CPU
- ✅ Ultra optimisé (llama.cpp)
- ✅ Supporte Q4, Q5, Q8
- ✅ Parfait pour serveur 24 Go RAM

## Utilisation

### 1. Configuration automatique (recommandé)

Le code détecte automatiquement CPU et utilise GGUF si disponible :

```python
from core import LLMAdapter, CoreConfig

# Configuration par défaut
config = CoreConfig(
    use_gguf=True,  # Activé par défaut
    quantize=True,
    quantization_bits=4
)

adapter = LLMAdapter(config)
```

**Comportement** :
- Si CPU détecté → cherche un modèle `.gguf` et l'utilise
- Si GPU détecté → utilise transformers + bitsandbytes (comme avant)
- Si aucun GGUF trouvé → fallback vers transformers (avec avertissement)

### 2. Spécifier un modèle GGUF explicitement

```python
config = CoreConfig(
    use_gguf=True,
    gguf_model_path="models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
)

adapter = LLMAdapter(config)
```

### 3. Désactiver GGUF (forcer transformers)

```python
config = CoreConfig(
    use_gguf=False,  # Désactiver GGUF
    quantize=True,
    quantization_bits=4
)

adapter = LLMAdapter(config)
# ⚠️ Nécessite GPU pour quantisation INT4
```

## Où trouver des modèles GGUF

### HuggingFace (recommandé)

1. Aller sur [HuggingFace Models](https://huggingface.co/models)
2. Chercher votre modèle (ex: `Qwen2.5-1.5B-Instruct`)
3. Filtrer par "GGUF" dans les tags
4. Télécharger un fichier `.gguf` (ex: `q4_k_m.gguf` pour Q4)

### Exemples de modèles GGUF populaires

- **Qwen2.5-1.5B-Instruct** : `bartowski/Qwen2.5-1.5B-Instruct-GGUF` (fichier: `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`)
- **Llama 3.2 3B** : `bartowski/Llama-3.2-3B-Instruct-GGUF`
- **Mistral 7B** : `TheBloke/Mistral-7B-Instruct-v0.2-GGUF`

### Formats de quantisation GGUF

| Format | Taille | Qualité | RAM requise |
|--------|--------|---------|-------------|
| Q4_K_M | ~1 GB | Bonne | ~2-3 GB |
| Q5_K_M | ~1.2 GB | Très bonne | ~2.5-3.5 GB |
| Q8_0 | ~1.8 GB | Excellente | ~3-4 GB |

**Recommandation** : `Q4_K_M` pour serveur 24 Go RAM.

## Structure des fichiers

```
LIA/
├── models/
│   └── qwen2.5-1.5b-instruct-q4_k_m.gguf  # Modèle GGUF
├── core/
│   ├── llm_adapter.py      # ✅ Support GGUF ajouté
│   ├── config.py            # ✅ Options GGUF ajoutées
│   └── requirements.txt     # ✅ llama-cpp-python ajouté
└── docs/
    └── MIGRATION_GGUF_CPU.md  # Ce document
```

## Détails techniques

### Méthodes ajoutées dans `LLMAdapter`

1. **`_find_gguf_model()`** : Cherche récursivement un fichier `.gguf`
2. **`_load_model_gguf()`** : Charge le modèle avec `llama-cpp-python`
3. **`_generate_gguf()`** : Génère des réponses avec l'API llama-cpp-python
4. **`_has_cuda()`** : Vérifie la disponibilité CUDA

### Modifications dans `CoreConfig`

- `use_gguf: bool = True` : Activer/désactiver GGUF
- `gguf_model_path: Optional[str] = None` : Chemin explicite vers modèle GGUF

### Détection automatique

```python
should_use_gguf = (
    self.config.use_gguf and 
    (self.device == "cpu" or not self._has_cuda())
)
```

## Installation

### 1. Installer llama-cpp-python

```bash
pip install llama-cpp-python
```

### 2. Télécharger un modèle GGUF

```bash
# Exemple : télécharger Qwen2.5-1.5B-Instruct Q4
# Option 1 : Utiliser le script fourni
python scripts/download_gguf_model.py

# Option 2 : Utiliser huggingface-cli
pip install huggingface_hub
huggingface-cli download bartowski/Qwen2.5-1.5B-Instruct-GGUF Qwen2.5-1.5B-Instruct-Q4_K_M.gguf --local-dir models
```

### 3. Tester

```python
from core import LLMAdapter, CoreConfig

config = CoreConfig(
    use_gguf=True,
    gguf_model_path="models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
)

adapter = LLMAdapter(config)
response = await adapter.generate("Bonjour, qui es-tu ?")
print(response)
```

## Avantages de GGUF

✅ **CPU-only** : Fonctionne sans GPU  
✅ **Optimisé** : llama.cpp est ultra-rapide  
✅ **Faible RAM** : Q4 utilise ~2-3 GB RAM  
✅ **Standard** : Format universellement supporté  
✅ **Qualité** : Dégradation minimale avec Q4_K_M  

## Limitations

⚠️ **Modèles GGUF requis** : Il faut télécharger un modèle déjà quantifié en GGUF  
⚠️ **Pas de fine-tuning** : GGUF est pour l'inférence uniquement  
⚠️ **Chat templates** : Certains modèles GGUF peuvent nécessiter un formatage manuel du prompt  

## Migration depuis l'ancien code

**Aucun changement nécessaire** si vous utilisez la configuration par défaut ! Le code détecte automatiquement CPU et utilise GGUF.

Pour forcer l'ancien comportement (transformers + bitsandbytes) :
```python
config = CoreConfig(use_gguf=False)
```

## Support

- Documentation llama-cpp-python : https://llama-cpp-python.readthedocs.io/
- Format GGUF : https://github.com/ggerganov/ggml/blob/master/docs/gguf.md
- HuggingFace GGUF models : https://huggingface.co/models?library=gguf

