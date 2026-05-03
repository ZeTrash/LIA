# Spécification LocalLLMAdapter

## Vue d'ensemble

`LocalLLMAdapter` est l'interface pour utiliser GPT-2 Small comme modèle LLM local, remplaçant les APIs externes (Gemini, OpenAI).

## Interface

### Classe LocalLLMAdapter

```python
class LocalLLMAdapter:
    """Adapter pour GPT-2 Small (modèle local vierge)."""
    
    def __init__(
        self,
        model_name: str = "gpt2",
        quantize: bool = True,
        device: str = "auto",  # "cpu", "cuda", "auto"
        cache_dir: str | None = None,
        max_memory_mb: int = 200,
        fallback_adapter: LLMAdapter | None = None
    ):
        """
        Initialise l'adapter GPT-2 Small.
        
        Args:
            model_name: Nom du modèle (gpt2, distilgpt2, etc.)
            quantize: Activer la quantisation INT4/INT8
            device: Device (cpu, cuda, auto)
            cache_dir: Répertoire de cache pour le modèle
            max_memory_mb: Mémoire maximale en MB
            fallback_adapter: Adapter de fallback (API externe) si erreur
        """
    
    async def send_message(
        self,
        message: str,
        context: MemoryContext | None = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Génère une réponse avec GPT-2 Small.
        
        Args:
            message: Message utilisateur
            context: Contexte mémoire (traits, souvenirs, objectifs)
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température de génération
            top_p: Top-p sampling
        
        Returns:
            Réponse générée
        
        Raises:
            LLMError: Si génération échoue (fallback si configuré)
        """
    
    def build_prompt(
        self,
        message: str,
        context: MemoryContext | None = None
    ) -> str:
        """
        Construit le prompt avec contexte mémoire.
        
        Args:
            message: Message utilisateur
            context: Contexte mémoire
        
        Returns:
            Prompt formaté
        """
    
    def load_model(self) -> None:
        """Charge le modèle GPT-2 Small."""
    
    def unload_model(self) -> None:
        """Décharge le modèle de la mémoire."""
    
    def get_memory_usage_mb(self) -> float:
        """Retourne l'utilisation mémoire en MB."""
```

## Format du prompt

### Structure

```
[Personnalité LIA]
{traits formatés}

[Souvenirs pertinents]
{souvenirs formatés}

[Objectifs de session]
{objectifs formatés}

[Conversation]
{message utilisateur}
```

### Exemple

```
[Personnalité LIA]
- Curiosité: élevée (0.85)
- Ton: curieux mais calme
- Style: réfléchi et analytique

[Souvenirs pertinents]
- Alice dirige le pôle Produit depuis 2023.
- L'utilisateur préfère des réponses concises.

[Objectifs de session]
- Préparer un résumé de meeting

[Conversation]
Peux-tu résumer la réunion RH ?
```

### Limites

- **Max tokens contexte** : 512 tokens (configurable)
- **Max tokens réponse** : 150 tokens par défaut
- **Priorisation** : Traits > Souvenirs récents > Objectifs

## Quantisation

### INT4 (recommandé)

- **Taille** : ~125 MB
- **RAM** : ~150-200 MB
- **Qualité** : Légère dégradation acceptable
- **Performance** : Bonne sur CPU

### INT8 (alternative)

- **Taille** : ~250 MB
- **RAM** : ~300-400 MB
- **Qualité** : Proche du FP32
- **Performance** : Excellente

### Implémentation

```python
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from transformers import BitsAndBytesConfig

# Quantisation INT4
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

model = GPT2LMHeadModel.from_pretrained(
    "gpt2",
    quantization_config=quantization_config,
    device_map="auto"
)
```

## Gestion des erreurs

### Fallback automatique

Si `LocalLLMAdapter` échoue, utiliser `fallback_adapter` (API externe) :

```python
try:
    response = await local_adapter.send_message(message, context)
except LLMError as e:
    if fallback_adapter:
        logger.warning(f"Local LLM failed, using fallback: {e}")
        response = await fallback_adapter.send_message(message, context)
    else:
        raise
```

### Erreurs possibles

- **OutOfMemoryError** : Modèle trop gros → Décharger, réduire quantisation
- **TimeoutError** : Génération trop lente → Réduire max_tokens
- **ModelNotFoundError** : Modèle non téléchargé → Télécharger automatiquement

## Configuration

### Variables d'environnement

```bash
LIA_LOCAL_LLM_MODEL=gpt2
LIA_LOCAL_LLM_QUANTIZE=true
LIA_LOCAL_LLM_DEVICE=auto
LIA_LOCAL_LLM_MAX_MEMORY_MB=200
LIA_LOCAL_LLM_CACHE_DIR=./models
```

### Fichier de configuration

```yaml
local_llm:
  model_name: "gpt2"
  quantize: true
  device: "auto"
  max_memory_mb: 200
  cache_dir: "./models"
  fallback_enabled: true
  fallback_provider: "openai"  # ou "gemini"
```

## Performance

### Métriques cibles

- **Latence** : < 2 secondes par réponse (CPU)
- **Mémoire** : < 200 MB RAM (quantisé INT4)
- **Qualité** : Cohérence avec personnalité stockée

### Optimisations

- **Cache modèle** : Garder en mémoire après premier chargement
- **Batch processing** : Optionnel pour plusieurs messages
- **GPU** : Utilisation automatique si CUDA disponible

## Tests

### Tests unitaires

- Chargement du modèle
- Construction du prompt
- Génération de réponse
- Gestion des erreurs
- Fallback

### Tests d'intégration

- Intégration avec memory_service
- Validation qualité des réponses
- Tests de performance


