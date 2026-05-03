# Système de Patterns V2 – Thèmes et Classification

**Date** : 2024-12  
**Statut** : 📋 Implémentation  
**Remplace** : Extension de `SYSTEME_PATTERNS.md`

---

## Vue d'ensemble

Le système V2 apporte **deux changements ciblés** au flux existant :

1. **Avant la planification** : Gemini choisit un thème parmi ceux disponibles en DB, correspondant à la requête. La planification cognitive utilise ensuite les patterns **filtrés par ce thème**.
2. **Apprentissage** : On **ajoute** une section au prompt d'origine (sans le remplacer) pour obtenir la sortie `{{theme_pattern},{B2, G3, G5}}` avec les directives appropriées.

Le thème `no_pattern` est utilisé pour les patterns par défaut (ex. seed de `clear_memory_db.py`).

---

## Architecture du flux

### Flux actuel (V1)

```
db_pattern → Planification cognitive (utilise le pattern) → Gemini apprentissage de pattern
```

**Format de sortie Gemini** : `{B2, G3, G5}` → parsé en `['B2', 'G3', 'G5']`

### Flux V2 (proposé)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 1 : Classification du thème (Gemini)                                 │
│                                                                             │
│ Prompt : Pour cette requête "{Requête}", voici les patterns disponibles     │
│ {liste_theme_pattern_dans_db}. Choisissez UN SEUL pattern auquel pourrait   │
│ appartenir la requête.                                                      │
│                                                                             │
│ Sortie : theme_pattern (ex: "salutation", "mémoire", "identité")              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 2 : Planification cognitive (inchangée)                                │
│                                                                             │
│ Utilise les patterns de la DB (filtrés par theme_pattern si disponible)     │
│ pour guider les choix de menus.                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 3 : Apprentissage de pattern (Gemini)                                 │
│                                                                             │
│ Le prompt d'origine est CONSERVÉ. On AJOUTE une section :                   │
│ Pour cette requête "{Requête}", voici les thèmes disponibles                │
│ {liste_theme_pattern_dans_db}. Vous avez le choix :                          │
│   - Sélectionner un thème existant auquel pourrait appartenir la requête   │
│   - OU indiquer un NOUVEAU theme_pattern si, et seulement si, la requête   │
│     ne peut être classée parmi aucun des thèmes existants.                   │
│                                                                             │
│ Format de réponse EXIGÉ : {{theme_pattern},{B2, G3, G5}}                    │
│                                                                             │
│ Sortie parsée : [[theme_pattern], 'B2', 'G3', 'G5']                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Format de réponse Gemini (V2)

### Avant (V1)

```
{B2, G3, G5}
→ ['B2', 'G3', 'G5']
```

### Après (V2)

```
{{theme_pattern},{B2, G3, G5}}
→ [[theme_pattern], 'B2', 'G3', 'G5']
```

Exemples valides :

- `{{salutation},{B3}}` → theme="salutation", séquence=["B3"]
- `{{mémoire},{B2, G4, G5}}` → theme="mémoire", séquence=["B2", "G4", "G5"]
- `{{nouveau_theme_custom},{B2, G1, G5}}` → nouveau thème créé, séquence=["B2", "G1", "G5"]
- `{{identité_utilisateur},{B2, G4, G5}}` → theme="identité_utilisateur", séquence=["B2", "G4", "G5"] pour des questions du type "Que connais-tu de moi ?"

---

## Modifications de la base de données

### Nouvelle table : `theme_patterns`

| Colonne      | Type   | Description                          |
|-------------|--------|--------------------------------------|
| theme_id    | String | Clé primaire (UUID)                  |
| theme_name  | String | Nom du thème (ex. "salutation")      |
| created_at  | DateTime | Date de création                   |

### Modification de la table `patterns`

| Colonne ajoutée | Type   | Description                                      |
|-----------------|--------|--------------------------------------------------|
| theme_pattern   | String | Thème associé (nullable pour rétrocompatibilité) |

La clé logique pour les recommandations devient : `(theme_pattern?, menu_context, prev_step)`.

- Si `theme_pattern` est `NULL`, le pattern reste utilisable comme en V1 (recommandation globale).
- Si `theme_pattern` est défini, la recommandation est spécifique au thème.

---

## API mémoire

### Nouvelles méthodes

- **`list_theme_patterns()`** : retourne la liste des noms de thèmes disponibles.
- **`add_theme_pattern(theme_name: str)`** : ajoute un thème s’il n’existe pas.

### Méthodes modifiées

- **`upsert_pattern(..., theme_pattern: Optional[str] = None)`** : ajout du paramètre optionnel.
- **`get_pattern_recommendation(..., theme_pattern: Optional[str] = None)`** : filtre optionnel par thème (priorité au pattern du thème, sinon fallback sur pattern sans thème).

---

## Thèmes initiaux (seed)

Thèmes proposés au démarrage (`init_theme_patterns.py`) :

- `no_pattern` – Pattern par défaut (utilisé par `clear_memory_db.py`)
- `identité` – Questions sur QUI EST LIA (ex. « Qui es-tu ? »)
- `identité_utilisateur` – Questions sur ce que LIA sait de l'utilisateur (ex. « Que connais-tu de moi ? »)


---

## Logs attendus

### Étape 1 (classification)

```
INFO:core.llm_adapter:📝 [PATTERNS] Classification thème – Requête: "..."
INFO:core.llm_adapter:✅ [PATTERNS] Thème classifié: no_pattern
```

### Étape 3 (apprentissage)

```
INFO:core.llm_adapter:📝 [PATTERNS] Réponse brute Gemini (patterns):
{{salutation},{B3}}
INFO:core.llm_adapter:✅ [PATTERNS] Suite recommandée par l'AGENT (parsée et valide): [['salutation'], 'B3']
INFO:core.llm_adapter:📚 [PATTERNS] Pattern mis à jour via AGENT: theme=salutation, ctx=base, prev=initial, rec=B3, ...
```

---

## Rétrocompatibilité

- Les patterns existants sans `theme_pattern` restent valides.
- Si aucun thème n’est fourni, `get_pattern_recommendation` se comporte comme en V1.
- Le parser accepte les deux formats :
  - `{B2, G3, G5}` → theme=None, séquence=["B2", "G3", "G5"]
  - `{{theme},{B2, G3, G5}}` → theme="theme", séquence=["B2", "G3", "G5"]

---

## Mise en place

Pour activer le système V2 sur une base existante :

```bash
# 1. Migration (ajoute theme_patterns + colonne theme_pattern)
python scripts/migrate_patterns_v2.py

# 2. Seed des thèmes initiaux
python scripts/init_theme_patterns.py
```

Pour une nouvelle installation, `create_all` crée automatiquement les tables. Exécuter uniquement `init_theme_patterns.py` pour peupler les thèmes.

---

## Prochaines étapes

1. ✅ Documenter le système (ce document)
2. ✅ Ajouter la table `theme_patterns` et la colonne `theme_pattern` à `patterns`
3. ✅ Implémenter l'étape 1 (classification Gemini)
4. ✅ Adapter le prompt et le parser de l'étape 3
5. ✅ Intégrer le thème dans le flux de planification et d'upsert

