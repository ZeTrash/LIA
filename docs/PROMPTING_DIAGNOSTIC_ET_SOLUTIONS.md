# Prompting LIA — Diagnostic & Solutions Cohérentes (Roadmap)

**Date** : 2026-02-16  
**Objectif** : Documenter les problèmes réels observés dans les prompts de LIA (GGUF + mémoire + autonomie), puis proposer des solutions cohérentes avec l’architecture du projet.

---

## Pourquoi on peut parler de “gros problèmes de prompt” ?

LIA fonctionne avec une **mémoire persistante** et une **identité** intégrées au prompt. Une petite erreur de format (ou un artefact injecté depuis la mémoire) peut :

- faire **régurgiter** une ancienne phrase au lieu de répondre,
- produire une réponse **tronquée** (ex: suffixe “2.”),
- dégrader la cohérence (“LIA répond à l’historique, pas à la question actuelle”),
- mélanger des conversations si le contexte n’est pas scindé par session.

L’échange “conscience vs mémoire” a révélé une combinaison de facteurs.

---

## Problèmes identifiés (avec ancrage repo)

### 1) Historique en “style narratif” (risque de régurgitation)

Dans le format “classique”, l’historique était injecté sous forme de narration :

- `Tu avais demandé: ...`
- `J'avais répondu: ...`

Ce format pousse parfois le modèle à **imiter** le style (réciter/continuer l’historique) au lieu de répondre à la question.

**Correctif appliqué (2026-02-16)** : historique rendu “chat réel” :

- `Utilisateur: ...`
- `LIA: ...`

**Fichier** : `core/llm_adapter.py`

---

### 2) Arrêts prématurés (“stop tokens”) trop agressifs en GGUF

Le moteur GGUF (llama-cpp) supporte une liste `stop=[...]`. Si on inclut des stops trop génériques (ex: `\n2.`), la génération peut être **coupée** dès que le modèle commence une liste numérotée.

Symptôme observé : réponses qui finissent par un “2.” ou qui s’arrêtent “bizarrement”.

**Correctif appliqué (2026-02-16)** :
- suppression des stops `\n1.` … `\n5.`
- suppression de stops “fragments d’identité” trop génériques (`Je m'appelle`, etc.)
- ajout d’un nettoyage de fin : suppression d’un `\d+.` parasite final

**Fichier** : `core/llm_adapter.py`

---

### 3) Incohérence d’en-tête pour la troncature (GGUF)

La troncature “intelligente” cherchait une section :
- `=== Conversation Actuelle ===`

Alors que le prompt construit utilise :
- `=== CONVERSATION ACTUELLE ===`

Résultat : parfois, la troncature ne trouve pas la section “question actuelle” et tombe sur un fallback moins fiable.

**Correctif appliqué (2026-02-16)** : la détection accepte les deux variantes.

**Fichier** : `core/llm_adapter.py`

---

### 4) Pollution par artefacts mémoire (“Session en cours: …”, numérotation, etc.)

Le système crée parfois un souvenir technique :
- `Session en cours: ...`

C’est utile pour “activer” la mémoire, mais c’est un **artefact** qui ne doit pas se retrouver dans les parties “humaines” du prompt (ou au moins doit être filtré).

**État actuel** :
- côté souvenirs (format classique), on filtre déjà `Session en cours:` dans certains cas
- côté Qwen chat-template, il existait une numérotation des souvenirs (`1. ...`, `2. ...`) : corrigée (pas de numérotation)

**Fichiers** :
- `core/llm_adapter.py`
- `core/memory_activator.py`

---

### 5) Mélange d’interactions (cross-session leakage)

La doc `docs/CONTEXTE_CONVERSATION.md` note que les interactions récentes sont récupérées “peu importe la session”.

Conséquence :
- plusieurs utilisateurs → historique mélangé
- un test/une session “pollue” la suivante
- le modèle répond à des éléments hors-contexte

**Fichiers** :
- `memory_service/store.py` (`get_context` / `recent_interactions`)
- `memory_service/memory_adapter.py`
- `core/memory_activator.py`

---

### 6) Compétition interne entre instructions (absence de hiérarchie explicite)

En production, le facteur le plus destructeur de cohérence est souvent la **compétition** entre blocs du prompt :

- identité (“je suis LIA…”)
- mémoire (“je me souviens…”, traits)
- historique (“Utilisateur/LIA: …”)
- question actuelle (“Utilisateur: …”)

Si le prompt est long, le modèle doit **deviner** quoi prioriser. Sans règle explicite, il peut :

- répondre à l’historique au lieu de la question,
- régurgiter des sections (“=== … ===”, “### …”),
- s’appuyer sur un souvenir hors-sujet.

**Solution structurelle recommandée** : ajouter une règle courte et non ambiguë de priorité (ordre strict).

---

## Principes de prompt cohérents avec le projet (guidelines)

### A) Un seul format conversationnel (chat) partout

**Règle** : historique et conversation actuelle doivent être au format :
- `Utilisateur: ...`
- `LIA: ...`

Éviter la narration (`Tu avais demandé`, `J’avais répondu`) et éviter la numérotation.

### B) Séparer strictement 4 zones

Dans cet ordre :

1. **Identité / système** : stable, court par défaut (version courte)
2. **Contexte mémoire** : traits + souvenirs filtrés + éventuellement objectifs
3. **Historique conversation** : 2–5 tours max, format chat
4. **Conversation actuelle** : question utilisateur + “LIA:”

### C) Stop tokens minimalistes

En GGUF, arrêter sur :
- début d’un nouveau message utilisateur (`\n\nUtilisateur:`)
- éventuellement des marqueurs de section (“=== … ===”) si et seulement si le modèle les réimprime

Ne jamais stopper sur des motifs “normaux” (listes numérotées, phrases d’identité).

### D) Mémoire : filtrer les artefacts techniques

Ne pas injecter en “souvenir” :
- `Session en cours: ...`
- logs ou fragments d’exécution
- “prompts complets” (ne stocker que l’essentiel)

### E) Hiérarchie explicite des instructions (priorité absolue)

Ajouter une règle **courte** (1–2 lignes) qui impose un ordre strict :

1. **Question actuelle** (répondre à ça, toujours)
2. **Historique récent** (contexte immédiat)
3. **Mémoire** (souvenirs/traits pertinents)
4. **Identité** (ton/style/valeurs, stable)

Objectif : réduire la régurgitation, les réponses hors-sujet et la confusion entre blocs.

---

## Solutions proposées (priorisées)

### Court terme (safe + impact fort)

1. **Unifier le format historique (chat réel)** ✅ (déjà appliqué)
2. **Stop tokens GGUF minimalistes** ✅ (déjà appliqué)
3. **Troncature : détection robuste de la question actuelle** ✅ (déjà appliqué)
4. **Outil de diagnostic de prompt** : CLI qui imprime :
   - prompt final,
   - taille approximative tokens,
   - sections détectées,
   - contexte mémoire réellement injecté.

### Moyen terme (cohérence + qualité)

1. **Scope par session** pour `recent_interactions`
   - `recent_interactions` doit être filtré par `session_id` (au moins dans l’interface web)
   - garder une mémoire “long terme” séparée (souvenirs) qui, elle, peut être globale

2. **Templates de prompt versionnés**
   - ex: `PromptTemplateV1`, `PromptTemplateV2`
   - faciliter rollback et tests

3. **Identité version courte/longue**
   - courte par défaut
   - longue seulement si la question porte sur l’identité/conscience

### Long terme (robustesse)

1. **Résumé conversationnel** (compression)
   - plutôt que 10 interactions brutes, garder un résumé + 2–3 tours récents

2. **Tests automatiques de prompt**
   - test “no narrative history”
   - test “no numbered stops”
   - test “question actuelle détectable”
   - test “pas d’artefacts Session en cours injectés”

---

## Liens utiles (repo)

- `core/llm_adapter.py` : construction prompt, GGUF stops, nettoyage réponse
- `core/memory_activator.py` : récupération contexte, création “Session en cours”
- `memory_service/store.py` : sélection `recent_interactions`
- `docs/LIMITES_PROMPTS.md` : budget tokens / redondance (complémentaire)
- `docs/CONTEXTE_CONVERSATION.md` : notes sur interactions récentes et sessions


