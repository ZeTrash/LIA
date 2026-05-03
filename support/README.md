# Support - Phase 4 : Noyau d'Appui (Gemini)

Service noyau d'appui pour LIA utilisant Gemini comme source de connaissance.

## Vue d'Ensemble

Le noyau d'appui sert de **première source de connaissance** pour LIA, comme un livre ou une encyclopédie. Il permet à LIA d'apprendre et d'explorer des sujets via Gemini API.

**Important** : Le noyau d'appui n'est **PAS** le moteur de génération (c'est le noyau primaire). C'est une source de connaissance externe.

## Structure

```
support/
├── __init__.py
├── config.py                  # Configuration du noyau d'appui
├── knowledge_source.py         # Interface abstraite pour sources de connaissance
├── gemini_adapter.py          # Adaptateur pour Gemini API
├── learning_service.py         # Service d'apprentissage via Gemini
├── requirements.txt           # Dépendances
└── tests/
    └── test_gemini.py         # Tests unitaires
```

## Installation

```bash
cd /opt/LIA
source venv/bin/activate
pip install -r support/requirements.txt
```

## Configuration

1. Copier le fichier de configuration :
```bash
cp config/api.conf.example config/api.conf
```

2. Éditer `config/api.conf` avec votre clé API Gemini :
```ini
gemini_api_key = VOTRE_CLE_API_GEMINI
```

## Utilisation

### Utilisation Basique

```python
from support import GeminiAdapter, SupportConfig

# Créer la configuration
config = SupportConfig()
config.load_from_file("config/api.conf")

# Créer l'adaptateur
adapter = GeminiAdapter(config)

# Vérifier la disponibilité
if adapter.is_available():
    # Interroger Gemini
    answer = await adapter.query("Qu'est-ce que l'intelligence artificielle ?")
    print(answer)
```

### Service d'Apprentissage

```python
from support import LearningService, SupportConfig
from memory_service import MemoryAdapter

# Créer le service d'apprentissage
config = SupportConfig()
config.load_from_file("config/api.conf")

memory = MemoryAdapter()
learning = LearningService(config=config, memory_adapter=memory)

# LIA apprend via Gemini
result = await learning.learn(
    "Qu'est-ce que la philosophie ?",
    save_to_memory=True
)

print(f"Réponse: {result['answer']}")
print(f"Sauvegardé dans mémoire: {result['memory_id']}")
```

### Exploration de Sujet

```python
# Explorer un sujet en profondeur
result = await learning.explore_topic(
    "intelligence artificielle",
    depth=2  # 2 questions
)

print(f"Connaissances apprises: {result['count']}")
for learning in result['learnings']:
    print(f"- {learning['question']}")
```

## Intégration avec la Mémoire

Le service d'apprentissage peut automatiquement sauvegarder les connaissances apprises dans la mémoire :

```python
# Configuration pour sauvegarder automatiquement
config = SupportConfig(
    auto_save_knowledge=True,  # Sauvegarder automatiquement
    enable_learning=True
)

learning = LearningService(config=config, memory_adapter=memory)

# La connaissance sera automatiquement sauvegardée
result = await learning.learn("Qu'est-ce que Python ?")
```

## Tests

```bash
cd /opt/LIA
source venv/bin/activate
pytest support/tests/test_gemini.py -v
```

## Phase 4 - Statut

✅ **Phase 4.1 : Intégration Gemini** - Terminé
- ✅ Structure créée (support/)
- ✅ GeminiAdapter implémenté
- ✅ Interface KnowledgeSource créée
- ✅ Tests unitaires créés

✅ **Phase 4.2 : Utilisation comme Source de Connaissance** - Terminé
- ✅ LearningService créé
- ✅ LIA peut interroger Gemini pour apprendre
- ✅ Connaissances journalisées dans mémoire
- ✅ Intégration avec cycle d'apprentissage

## Concepts Clés

- **Noyau d'Appui** = Source de connaissance (comme un livre)
- **Noyau Primaire** = Moteur de génération (GPT-2)
- **LearningService** = Service permettant à LIA d'apprendre via le noyau d'appui
- **Auto-sauvegarde** = Les connaissances apprises peuvent être automatiquement sauvegardées dans la mémoire

