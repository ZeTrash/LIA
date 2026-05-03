# Noyau Primaire (Core)

**Rôle** : Moteur de génération de réponses avec GPT-2

---

## Vue d'Ensemble

Le noyau primaire est responsable de la génération de réponses à partir de prompts. Il utilise GPT-2 Small comme moteur de génération.

**Important** : Le noyau primaire n'est **PAS** la source de connaissance, c'est le moteur de génération. La source de connaissance est le noyau d'appui (Gemini).

---

## Composants

### LLMAdapter

Adaptateur pour GPT-2 Small qui :
- Charge le modèle avec quantisation optionnelle (INT4/INT8)
- Construit des prompts avec contexte mémoire
- Génère des réponses personnalisées
- Gère le cache du modèle (évite rechargement)

### CoreConfig

Configuration du noyau primaire :
- Paramètres de génération (température, max_length, etc.)
- Configuration du modèle
- Paramètres de quantisation
- Contrôle d'auto-calibration

---

## Utilisation

### Installation

```bash
pip install -r requirements.txt
```

### Exemple Basique

```python
from core import LLMAdapter, CoreConfig

# Créer configuration
config = CoreConfig(
    model_name="gpt2",
    max_length=100,
    temperature=0.7
)

# Créer adaptateur
adapter = LLMAdapter(config)

# Générer une réponse
response = await adapter.generate(
    message="Bonjour, comment vas-tu ?",
    context={
        "traits": [{"label": "Ton", "value": "Amical"}],
        "memories": []
    }
)
```

### Avec Contexte Mémoire

```python
context = {
    "traits": [
        {"label": "Ton", "value": "Amical et chaleureux"},
        {"label": "Style", "value": "Conversationnel"}
    ],
    "memories": [
        {"content": "L'utilisateur aime la philosophie"}
    ],
    "session_goals": [
        {"description": "Explorer la philosophie existentielle"}
    ]
}

response = await adapter.generate(
    message="Parle-moi de la philosophie",
    context=context
)
```

### Auto-Calibration

LIA peut modifier les paramètres :

```python
# Mettre à jour la température
adapter.update_config(temperature=0.9)

# Mettre à jour plusieurs paramètres
adapter.update_config(
    temperature=0.8,
    max_length=150,
    repetition_penalty=1.3
)
```

---

## Configuration

### Paramètres Disponibles

- `model_name` : Nom du modèle (défaut: "gpt2")
- `device` : Device ("auto", "cpu", "cuda")
- `max_length` : Longueur max de la réponse (défaut: 100)
- `temperature` : Température de génération (défaut: 0.7)
- `top_p` : Top-p sampling (défaut: 0.9)
- `top_k` : Top-k sampling (défaut: 50)
- `repetition_penalty` : Pénalité de répétition (défaut: 1.2)
- `quantize` : Activer quantisation (défaut: True)
- `quantization_bits` : Bits de quantisation (4 ou 8, défaut: 4)
- `max_prompt_length` : Longueur max du prompt (défaut: 512)
- `enable_auto_calibration` : Permettre auto-modification (défaut: True)

---

## Tests

```bash
pytest core/tests/
```

**Note** : Les tests nécessitent `transformers` et `torch` installés. Certains tests sont marqués `@pytest.mark.skip` si ces dépendances ne sont pas disponibles.

---

## Architecture

```
LLMAdapter
    ├── CoreConfig (configuration)
    ├── Model (GPT-2, cache global)
    ├── Tokenizer (GPT-2, cache global)
    ├── build_prompt() (construction avec contexte)
    ├── generate() (génération réponse)
    └── update_config() (auto-calibration)
```

---

## Limitations

- GPT-2 a une limite de 1024 tokens (prompt + réponse)
- Le prompt est limité à 512 tokens pour laisser de la place à la réponse
- Qualité limitée comparée à des modèles plus récents
- Nécessite GPU pour de meilleures performances (optionnel)

---

## Références

- **Architecture** : `../docs/ARCHITECTURE.md`
- **Concepts** : `../docs/CONCEPTS.md`
- **Plan de refonte** : `../docs/PLAN_REFONTE_PROJET.md`

---

**Date de création** : 2024-12-19

