## Implémentation Phase "exemple_process" (Mode Menu Minimal + Prompt Canonique)

**Date** : 2026-02-17  
**Contexte** : Implémentation concrète de la phase de départ décrite dans `exemple_process.md`, avec focus sur:
- la boucle de menus interne,
- un prompt final simple et canonique,
- sans apprentissage de patterns ni métriques complexes,
- en utilisant un modèle GGUF (llama.cpp) en mode chat.

---

## 1. Objectif de cette phase

Cette phase sert à:

- **Observer** la boucle cognitive "menus → choix → exécution → RESPOND" de manière lisible dans les logs, comme dans `exemple_process.md`.
- **Limiter** temporairement la complexité (vérification, apprentissage, mémoire sélective, métriques) pour se concentrer sur:
  - la forme des prompts internes,
  - la forme du prompt final,
  - la stabilité des réponses (éviter le code ou la méta-doc aberrante sur des requêtes simples comme "Bonjour").
- **Préparer** une architecture de prompts canonique (sections) qui pourra ensuite être enrichie (mémoire, identité, etc.).

Cette phase n’est pas le système complet décrit dans `ARCHITECTURE_ET_PLAN.md`, mais un **sous-ensemble contrôlé**, dédié au debug et à la validation des idées de `exemple_process.md`.

---

## 2. Activation du Mode "Menu Minimal"

### 2.1. Flag global

Dans `core/llm_adapter.py`:

- Flag global:
  - `DEBUG_MINIMAL_MENU_LOOP: bool`
- Valeur par défaut:
  - **True** si la variable d’environnement `LIA_DEBUG_MINIMAL_MENU_LOOP` n’est pas définie.
  - Sinon, interprétation classique (`"1"`, `"true"`, `"yes"`, `"oui"` → True).

### 2.2. Effets fonctionnels

Quand `DEBUG_MINIMAL_MENU_LOOP` est **activé**:

- **PatternLearner**:
  - Non initialisé.
- **SelfVerifier**:
  - Non initialisé.
- **MemoryManager** (sélection et nettoyage mémoire):
  - Non initialisé.
- **CognitiveSafeguards / CognitiveOptimizer / CognitiveMetrics**:
  - Toujours initialisables pour garder la structure, mais:
    - logs détaillés réduits,
    - usage minimal dans la boucle.
- Dans `_generate_with_planner`:
  - **Phase vérification**: sautée.
  - **Phase apprentissage de patterns**: sautée.
  - **Phase mémorisation sélective**: sautée.
  - **Phase métriques**: sautée.

L’idée est de garder:

> Entrée utilisateur → Planificateur (menus) → Choix RESPOND → Prompt final → Réponse utilisateur

sans les couches d’optimisation/apprentissage autour.

---

## 3. Boucle de Menus Interne

### 3.1. Construction du menu

Dans `_generate_with_planner`, pour chaque itération `i = 1..max_iterations`:

1. Appel à `self.cognitive_planner.build_action_menu(...)`:
   - Construit la liste des actions possibles pour cette étape.
2. Log dans les logs LIA:
   - `📌 [LLM_ADAPTER] Menu proposé (itération i/N, K actions):`
   - 1 ligne par action, avec:
     - description lisible (`_describe_action`),
     - type (`ActionType`),
     - paramètres tronqués si nécessaire.

### 3.2. Description des actions (`_describe_action`)

Fonction `_describe_action(a: Action) -> str`:

- `CONSULT_PATTERNS` → "Consulter les patterns préférés."
- `CONSULT_IDENTITY` → "Connaitre mon identité."
- `CONSULT_TRAITS` → "Connaitre mes traits."
- `CONSULT_MEMORY` / `CONSULT_INTERACTIONS` / `CONSULT_MEMORIES` →
  - "Consulter ma mémoire / interactions récentes."
- `SEARCH_MEMORY` → "Rechercher une information spécifique dans la mémoire."
- `QUERY_EXTERNAL` → "Consulter une source externe (Gemini)."
- `RESPOND` → "Répondre à la requête de l'utilisateur."

Ces descriptions sont **utilisées uniquement dans les menus** pour rendre les logs explicites.

### 3.3. Format canonique du prompt de décision (`_decision_prompt`)

Le menu envoyé à l’agent prend désormais la forme:

```text
=== HISTORIQUE INTERNE ===
Pour traiter la requette de l'utilisateur vous avez decidée de choisir de consulter votre mémoire.
Pour traiter la requette de l'utilisateur vous avez decidée de choisir de connaitre votre identité.
...

=== MENU D'ACTIONS INTERNES ===
Voici la liste d'actions possibles pour continuer le traitement de la demande de l'utilisateur :

1. Connaitre mon identité.
2. Consulter ma mémoire / interactions récentes.
3. Répondre à la requête de l'utilisateur.

Important: Pour continuer, écrire uniquement 1 ou 2 ou 3.
```

Points importants:

- **Section `HISTORIQUE INTERNE`**:
  - Contient un résumé textuel des actions déjà choisies (voir section 4).
  - N’existe qu’à partir de la 2ᵉ itération (après un ou plusieurs choix).
- **Section `MENU D'ACTIONS INTERNES`**:
  - Liste numérotée des actions.
  - Règle de format minimaliste:
    - "Important: Pour continuer, écrire uniquement 1." (ou "1 ou 2 ou 3").
  - On ne dit pas “réponds comme ceci ou comme cela”, on indique juste **le canal attendu** (un entier).

---

## 4. Historique Interne des Choix

Pour réaliser l’idée:

> “Pour traiter la requette de l'utilisateur vous avez decidée de choisir de consulter votre mémoire.”

on garde un historique `chosen_actions` dans `_generate_with_planner`, et on le transforme en texte à chaque itération.

### 4.1. Règles de résumé

Pour chaque action passée (`past_action`):

- **Mémoire / interactions**:
  - `CONSULT_MEMORY`, `CONSULT_INTERACTIONS`, `CONSULT_MEMORIES` →
    - "choisir de consulter votre mémoire."
- **Identité**:
  - `CONSULT_IDENTITY` →
    - "choisir de connaitre votre identité."
- **Traits**:
  - `CONSULT_TRAITS` →
    - "choisir de connaitre vos traits."
- **Exploration mémoire**:
  - `SEARCH_MEMORY` →
    - "choisir d'explorer votre mémoire."
- **Source externe**:
  - `QUERY_EXTERNAL` →
    - "choisir de consulter une source externe."
- **Réponse**:
  - `RESPOND` →
    - "choisir de repondre à la requette de l'utilisateur."

Puis on construit des phrases:

> "Pour traiter la requette de l'utilisateur vous avez decidée de \<desc_choice\>"

et on les place dans `HISTORIQUE INTERNE`.

### 4.2. Limitation de taille

- On ne garde que les **N dernières actions** (par ex. 5) pour éviter de gonfler le prompt.

---

## 5. Gestion robuste des erreurs de menu

Cas: le modèle ne répond pas par un entier valide (par ex. renvoie "2. Passer à l'étape suivante...").

### 5.1. Première tentative

1. On génère `decision_prompt = _decision_prompt(menu, history_text)`.
2. On appelle `_generate_decision_text(decision_prompt)`.
3. On essaie de parser la réponse avec `_parse_choice` (extraction du premier entier).

### 5.2. Relance du menu

Si `_parse_choice` retourne `None`:

1. On construit un nouveau prompt:

   ```text
   Réponse incorrecte. Tu dois choisir une option dans le menu.

   === HISTORIQUE INTERNE ===
   ...

   === MENU D'ACTIONS INTERNES ===
   ...
   ```

2. On appelle à nouveau `_generate_decision_text(...)`.
3. On parse à nouveau.

### 5.3. Fallback déterministe

Si, **après relance**, la réponse reste invalide:

- On choisit une action par défaut:
  - première action non-RESPOND, ou RESPOND sinon,
- et on logge:

> "⚠️ [LLM_ADAPTER] Choix non parsable après relance, fallback interne vers: …"

---

## 6. Prompt Final Canonique

Une fois que la boucle de menus a choisi `RESPOND`, `_generate_with_planner` construit un **prompt final canonique**, au format par sections.

### 6.1. Construction de l’historique pour le final

On reprend `chosen_actions` et on les résume une seconde fois, cette fois pour le prompt final, avec une légère variation de style (tutoiement explicite):

> "Pour traiter la demande de l'utilisateur, tu as décidé de choisir de consulter ta mémoire."

Ces lignes forment le bloc `HISTORIQUE INTERNE` du prompt final.

### 6.2. Format complet du prompt final

Le prompt final a la forme:

```text
=== HISTORIQUE INTERNE ===
Pour traiter la demande de l'utilisateur, tu as décidé de choisir de répondre directement à la demande de l'utilisateur.

=== DEMANDE UTILISATEUR ===
"Bonjour"

=== STYLE ===
Cette section décrit ton style général et n'est pas une réponse à l'utilisateur.
Ton style par défaut est de répondre à la demande de l'utilisateur en langage naturel, de manière claire et compréhensible.

=== FORMAT ===
HISTORIQUE INTERNE : résumé de tes actions internes (contexte).
DEMANDE UTILISATEUR : la question / demande à traiter.
STYLE : ton style général (contexte).
SORTIE LIA : ce que tu envoies à l'utilisateur.

=== SORTIE LIA ===
```

**Important**:

- Aucune instruction du type:
  - "Tu dois répondre X"
  - "Ne fais jamais Y"
  - "Réponds sans code"
- On fournit:
  - un **contexte structuré** (historique),
  - la **demande brute**,
  - une **description du style général**,
  - une **explication des sections**.
- LIA reste libre de choisir **ce qu’elle écrit** dans `SORTIE LIA`, mais la structuration rend beaucoup moins probable la génération de méta-texte/débogage dans la sortie utilisateur.

---

## 7. Intégration avec le Modèle GGUF (llama.cpp)

### 7.1. Chargement GGUF avec `chat_format`

Dans `_load_model_gguf`:

- On détecte si le nom de fichier contient:
  - `"llama-3"` → `chat_format="llama-3"`,
  - `"llama-2"` → `chat_format="llama-2"`.
- On passe `chat_format` à `llama_cpp.Llama(...)`.

Effet:

- Permet à `llama.cpp` d’appliquer le **template chat** adapté.

### 7.2. `_generate_gguf` en mode chat

#### Avant

- On utilisait `self.model(...)` en mode completion brut avec le prompt concaténé.
- Toutes les sections (`HISTORIQUE`, `DEMANNDE`, `STYLE`, etc.) étaient vues comme du texte homogène.

#### Maintenant

1. On loggue toujours le prompt complet (pour debug).
2. Si `self.model` expose `create_chat_completion`:
   - On sépare:
     - **System**:
       - Tout ce qui est **avant** `=== DEMANDE UTILISATEUR ===` (typiquement `HISTORIQUE`, `STYLE`, `FORMAT`).
       - En enlevant toute section éventuelle `=== SORTIE LIA ===` dans cette partie.
     - **User**:
       - Le contenu brut de la section `DEMANDE UTILISATEUR` (jusqu’à la prochaine section).
   - On construit:

     ```python
     messages = [
       {"role": "system", "content": system_content},
       {"role": "user", "content": user_content},
     ]
     ```

   - On appelle:

     ```python
     self.model.create_chat_completion(
         messages=messages,
         max_tokens=...,
         temperature=...,
         ...
         stop=["\n\n\n", "=== HISTORIQUE", "=== DEMANDE", "=== STYLE", "=== FORMAT", "=== SORTIE"],
     )
     ```

3. On extrait la réponse:
   - `output["choices"][0]["message"]["content"]`.

4. Si `create_chat_completion` n’est pas disponible:
   - On revient au mode **completion brut** historique (fallback).

### 7.3. Effets observés

Sur des requêtes simples comme `"Bonjour"`:

- Avant:
  - Réponses mélangeant:
    - "Bonjour..." + méta-doc (`=== REFAIR L'ÉTAT ===`, "MODELES DE REÇUS", etc.).
- Maintenant:
  - Sortie propre:
    - `"Bonjour ! Comment puis-je vous aider aujourd'hui ?"`,  
    - sans sections supplémentaires.

La **grande différence** vient de:

- l’utilisation du **mode chat** (system/user),
- plus que de règles dures dans le texte du prompt.

---

## 8. Nettoyage de Sortie (`_clean_response`)

La fonction `_clean_response` est conservée pour:

- supprimer:
  - les sections méta remontées par erreur (`=== Conversation ...`, `=== PRINCIPES ...`, etc.),
  - les interactions fictives (`Utilisateur : ...`, `LIA : ...`),
  - certains formats techniques (`Réponse :`, `Question :`).
- C’est un **filet de sécurité**, par-dessus:
  - la nouvelle structure des prompts,
  - le mode chat GGUF.

---

## 9. Limites et Pistes Suivantes

### 9.1. Limites actuelles

- Mode "menu minimal" désactive:
  - Self-verification,
  - Apprentissage de patterns,
  - Mémoire sélective,
  - Métriques d’exécution.
- La mémoire est **consultée** (via `MemoryActivator`) dans `_generate_internal`, mais:
  - en mode planner minimal, le prompt final n’inclut pas encore:
    - traits détaillés,
    - souvenirs,
    - interactions passées.

### 9.2. Pistes d’évolution

1. **Réactiver progressivement**:
   - SelfVerifier,
   - PatternLearner,
   - MemoryManager,
   dans ce même cadre de prompt canonique.
2. **Étendre le format canonique**:
   - Ajouter des sections optionnelles:
     - `=== IDENTITÉ ===`,
     - `=== CONTEXTE MÉMOIRE ===`,
     - `=== INTERACTIONS RÉCENTES ===`,
   - tout en gardant:
     - `=== DEMANDE UTILISATEUR ===`,
     - `=== SORTIE LIA ===`,
     comme cœur.
3. **Unifier le format** entre:
   - `_generate_internal` (mode sans planner),
   - `_generate_with_planner` (mode avec menus),
   - pour que LIA ait toujours la même structure logique quel que soit le chemin de génération.

---

## 10. Résumé

Cette phase implémente:

- Un **mode debug minimal** aligné avec `exemple_process.md`, où:
  - on observe la boucle de menus,
  - les prompts internes et finaux sont en **format canonique par sections**,
  - les composants d’apprentissage et de métriques sont désactivés.
- Une intégration plus propre avec les modèles GGUF (`llama.cpp`) en **mode chat**, réduisant radicalement les fuites de prompt et les sorties aberrantes (code, méta-doc).
- Un **résumé interne des actions** réinjecté dans chaque menu et dans le prompt final, permettant à LIA de “se voir penser” sans perdre son autonomie sur la forme de la réponse utilisateur.

Ce document sert de référence d’implémentation pour cette phase et de base pour les phases suivantes (réactivation progressive de SelfVerifier, PatternLearner, MemoryManager, etc.).


