# Sandbox de Prompting

Espace isolé pour travailler sur le système de prompting de LIA, conformément à la conclusion de `docs/brain_architecture/concept.md`.

## Objectif

- Charger le modèle pour envoyer des prompts et évaluer les réponses
- Analyser les prompts envoyés et les réponses du modèle
- Préparer le modèle canonique et des contenus pour au moins 5 scénarios multi-tours
- Enregistrer tous les échanges dans des fichiers

## Structure

```
prompting_sandbox/
├── README.md           # Ce fichier
├── canonical_model.py  # Modèle canonique du prompt (sections structurées)
├── conversations/      # 5+ conversations prédéfinies
│   ├── conv_01_identite.json
│   ├── conv_02_prompt_noise.json
│   ├── conv_03_memory_retrieval.json
│   ├── conv_04_long_context.json
│   └── conv_05_suite_continue.json
├── run_experiments.py  # Script principal
└── outputs/            # Échanges enregistrés (généré à l'exécution)
    └── exchanges_YYYYMMDD_HHMMSS.json
```

## Modèle canonique

Le format canonique est défini dans `canonical_model.py` et suit la structure :

- **IDENTITÉ** : qui est LIA
- **HISTORIQUE INTERNE** : résumé des actions internes (optionnel)
- **CONTEXTE CONVERSATIONNEL** : échanges récents (optionnel)
- **STYLE** : style général de réponse
- **FORMAT** : explication des sections
- **DEMANDE UTILISATEUR** : la question à traiter
- **SORTIE LIA** : invite à générer

## Utilisation

```bash
cd /opt/LIA
source venv/bin/activate  # si applicable

# Exécuter toutes les conversations
python -m prompting_sandbox.run_experiments

# Exécuter comme une conversation continue (contexte accumulé)
python -m prompting_sandbox.run_experiments --continuous-session

# Forcer une petite fenêtre de contexte (ex: 3 tours) pour stresser la stabilité
python -m prompting_sandbox.run_experiments --continuous-session --context-turns 3

# Limiter à certaines conversations
python -m prompting_sandbox.run_experiments --conversations conv_01 conv_03

# Spécifier le dossier de sortie
python -m prompting_sandbox.run_experiments --output-dir ./mes_resultats
```

## Format des fichiers d'échanges

Chaque exécution produit un fichier JSON `exchanges_YYYYMMDD_HHMMSS.json` contenant :

```json
{
  "meta": {
    "timestamp": "...",
    "model": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
    "conversations_count": 5
  },
  "exchanges": [
    {
      "conversation_id": "conv_01",
      "turn": 1,
      "user_message": "Qui es-tu ?",
      "prompt_sent": "=== IDENTITÉ ===\n...",
      "model_response": "...",
      "prompt_length_chars": 1234,
      "response_length_chars": 256
    }
  ]
}
```

Une exécution produit aussi :

- `exchanges_YYYYMMDD_HHMMSS.jsonl` : 1 échange par ligne (pratique pour analyser/filtrer rapidement)
- `transcript_YYYYMMDD_HHMMSS.md` : transcript lisible (message, prompt envoyé, réponse)

## Prérequis

- Modèle GGUF dans `models/` (Qwen2.5-7B ou Llama-3.2-3B)
- `llama-cpp-python` installé pour le chargement GGUF

## Étapes suivantes (concept.md)

1. **Étape 1** : Modèle de prompt fixe (performing jusqu'à réponses stables)
2. **Étape 2** : Support de la métacognition
3. **Étape 3** : Modèle dynamique avec la métacognition
