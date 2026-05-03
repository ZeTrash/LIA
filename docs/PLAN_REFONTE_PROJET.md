# Plan de Refonte Complète du Projet LIA

**Date** : 2024-12-19  
**Objectif** : Reprendre le projet à zéro avec une architecture propre alignée sur la vision clarifiée  
**Approche** : Développement étape par étape avec validation à chaque étape

---

## Contexte et Justification

### Pourquoi une Refonte ?

1. **Architecture actuelle** : Complexité accumulée, incohérences avec la vision clarifiée
2. **Concepts clarifiés** : Nouvelles compréhensions des noyaux, sources de connaissance, contrôle des paramètres
3. **Vision nette** : Besoin d'une architecture propre depuis le début, alignée sur la vision

### Principes de la Refonte

- ✅ **Simplicité** : Commencer simple, ajouter progressivement
- ✅ **Validation** : Valider chaque étape avant de passer à la suivante
- ✅ **Documentation** : Documenter chaque concept et décision
- ✅ **Architecture propre** : Structure claire dès le départ

---

## Phase 0 : Préparation et Sauvegarde

### Étape 0.1 : Sauvegarde de l'Existant

**Objectif** : Préserver le travail existant tout en repartant à zéro

**Actions** :
1. Créer un dossier `_archive/` à la racine du projet
2. Déplacer les dossiers suivants dans `_archive/` :
   - `memory_service/`
   - `simulation_service/`
   - `charge_timeline/`
   - `tools/`
   - `docs/` (sauf les documents de vision et refonte)
3. Créer `_archive/README.md` expliquant le contenu et la date de sauvegarde

**Structure proposée** :
```
LIA/
├── _archive/                    # Ancien code sauvegardé
│   ├── memory_service/
│   ├── simulation_service/
│   ├── charge_timeline/
│   ├── tools/
│   └── README.md
├── docs/                        # Nouvelle documentation
│   ├── RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md
│   ├── ANALYSE_COHERENCE_REVISION.md
│   └── PLAN_REFONTE_PROJET.md (ce fichier)
├── config/                      # Configuration (conservée)
│   ├── api.conf.example
│   └── api.conf
└── README.md                    # Nouveau README
```

### Étape 0.2 : Récupération des Concepts Essentiels

**Objectif** : Extraire les concepts clés de l'ancien projet

**Concepts à récupérer** :

1. **Mémoire persistante** (de `memory_service/`)
   - Structure de données (Traits, Souvenirs, Interactions)
   - API REST pour accès mémoire
   - Système de gouvernance

2. **Architecture modulaire** (de `simulation_service/`)
   - Système d'adapters
   - Orchestration multi-agent
   - Portails d'interaction

3. **Autonomie** (de `charge_timeline/etape2_6/`)
   - Scheduler autonome
   - Objectifs personnels
   - Auto-recherche, auto-évaluation, auto-réflexion

4. **Modèle local** (de `charge_timeline/etape2_5/`)
   - LocalLLMAdapter pour Qwen2.5-1.5B-Instruct 4 bits
   - Intégration avec mémoire

**Document à créer** : `docs/CONCEPTS_RECUPERES.md`

---

## Phase 1 : Fondations (Étape 1)

### Vision Clarifiée

**Architecture cible** :
```
┌─────────────────────────────────────────┐
│              LIA Agent                   │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Noyau Primaire                  │  │
│  │  Qwen2.5-1.5B-Instruct 4 bits (léger, moteur génération)│  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Noyau d'Appui (API)              │  │
│  │  Gemini (première source          │  │
│  │  de connaissance, comme un livre) │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Mémoire                         │  │
│  │  Base de données locale          │  │
│  │  (personnalité, souvenirs)       │  │
│  └──────────────────────────────────┘  │
│                                         │
│  Canaux d'interaction :                │
│  • Utilisateur                         │
│  • Noyau d'appui (Gemini)              │
└─────────────────────────────────────────┘
```

**Concepts clés** :
- **Noyau primaire** (Qwen2.5-1.5B-Instruct 4 bits) = Moteur de génération
- **Noyau d'appui** (Gemini) = Première source de connaissance (comme un livre)
- **Mémoire** = Base de données locale (personnalité, souvenirs)
- **Contrôle complet** = LIA peut modifier tous ses paramètres

### Étape 1.1 : Structure de Base

**Objectif** : Créer la structure minimale du projet

**Actions** :
1. Créer la structure de dossiers de base
2. Créer `README.md` avec vision clarifiée
3. Créer `docs/ARCHITECTURE.md` avec architecture cible
4. Créer `docs/CONCEPTS.md` avec concepts clés

**Structure proposée** :
```
LIA/
├── README.md
├── .gitignore
├── config/
│   ├── api.conf.example
│   └── api.conf
├── docs/
│   ├── RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md
│   ├── ARCHITECTURE.md
│   ├── CONCEPTS.md
│   └── PLAN_REFONTE_PROJET.md
└── _archive/                    # Ancien code
```

### Étape 1.2 : Documentation de la Vision

**Objectif** : Documenter clairement la vision et les concepts

**Documents à créer/mettre à jour** :

1. **`docs/ARCHITECTURE.md`** :
   - Architecture cible clarifiée
   - Distinction noyau primaire vs noyau d'appui
   - Rôle de Gemini comme première source de connaissance
   - Canaux d'interaction

2. **`docs/CONCEPTS.md`** :
   - Noyau primaire (Qwen2.5-1.5B-Instruct 4 bits) = moteur de génération
   - Noyau d'appui (Gemini) = source de connaissance (comme un livre)
   - Noyaux secondaires = même chose que noyaux d'appui
     - Local = support cognitif direct
     - API = source d'infos comme livre
   - Contrôle complet des paramètres
   - Mémoire persistante

3. **`README.md`** :
   - Vision du projet
   - Architecture simplifiée
   - Plan de développement étape par étape

**Critères de validation** :
- ✅ Tous les concepts sont clairement documentés
- ✅ Architecture cible est définie
- ✅ Pas d'ambiguïté sur les rôles des composants

---

## Phase 2 : Noyau Primaire (Étape 2)

### Étape 2.1 : Intégration Qwen2.5-1.5B-Instruct 4 bits

**Objectif** : Intégrer Qwen2.5-1.5B-Instruct 4 bits comme noyau primaire (moteur de génération)

**Actions** :
1. Créer `core/` pour le noyau primaire
2. Implémenter `LocalLLMAdapter` pour Qwen2.5-1.5B-Instruct 4 bits
3. Tests basiques de génération

**Structure** :
```
LIA/
└── core/
    ├── __init__.py
    ├── llm_adapter.py          # LocalLLMAdapter pour Qwen2.5-1.5B-Instruct 4 bits
    ├── config.py               # Configuration noyau
    └── tests/
        └── test_llm_adapter.py
```

**Critères de validation** :
- ✅ Qwen2.5-1.5B-Instruct 4 bits peut générer des réponses
- ✅ Adapter fonctionne de manière isolée
- ✅ Tests passent

### Étape 2.2 : Configuration et Paramètres

**Objectif** : Système de configuration avec contrôle complet des paramètres

**Actions** :
1. Créer système de configuration
2. Permettre modification de tous les paramètres (température, max_length, etc.)
3. Stocker paramètres dans mémoire (pour auto-modification future)

**Critères de validation** :
- ✅ Tous les paramètres sont configurables
- ✅ Paramètres peuvent être modifiés
- ✅ Paramètres sont persistants

---

## Phase 3 : Mémoire (Étape 3)

### Étape 3.1 : Service Mémoire de Base

**Objectif** : Créer le service mémoire minimal

**Actions** :
1. Créer `memory_service/` avec structure minimale
2. Implémenter base de données (SQLite)
3. Modèles de base : Traits, Souvenirs

**Structure** :
```
LIA/
└── memory_service/
    ├── __init__.py
    ├── models.py               # Traits, Souvenirs
    ├── db.py                   # Base de données
    ├── api.py                  # API REST
    └── tests/
        └── test_memory.py
```

**Critères de validation** :
- ✅ Base de données créée
- ✅ Modèles fonctionnent
- ✅ API REST basique fonctionne

### Étape 3.2 : Intégration Noyau Primaire ↔ Mémoire

**Objectif** : Connecter le noyau primaire à la mémoire

**Actions** :
1. Le noyau primaire récupère le contexte depuis mémoire
2. Le noyau primaire journalise les interactions dans mémoire
3. Tests d'intégration

**Critères de validation** :
- ✅ Noyau primaire utilise le contexte mémoire
- ✅ Interactions sont journalisées
- ✅ Tests d'intégration passent

---

## Phase 4 : Noyau d'Appui (Étape 4)

### Étape 4.1 : Intégration Gemini

**Objectif** : Intégrer Gemini comme noyau d'appui (première source de connaissance)

**Actions** :
1. Créer `support/` pour les noyaux d'appui
2. Implémenter `GeminiAdapter` pour interroger Gemini
3. Créer le "canal d'échange avec le noyau d'appui"

**Structure** :
```
LIA/
└── support/
    ├── __init__.py
    ├── gemini_adapter.py       # Adapter pour Gemini API
    ├── knowledge_source.py     # Interface source de connaissance
    └── tests/
        └── test_gemini.py
```

**Critères de validation** :
- ✅ Gemini peut être interrogé via API
- ✅ Adapter fonctionne
- ✅ Canal d'échange existe

### Étape 4.2 : Utilisation comme Source de Connaissance

**Objectif** : Permettre à LIA d'apprendre via Gemini

**Actions** :
1. Créer système où LIA peut interroger Gemini pour apprendre
2. Journaliser les connaissances apprises dans mémoire
3. Intégrer dans le cycle d'apprentissage

**Critères de validation** :
- ✅ LIA peut interroger Gemini pour apprendre
- ✅ Connaissances sont journalisées
- ✅ Intégration dans cycle d'apprentissage

---

## Phase 5 : Canaux d'Interaction (Étape 5)

### Étape 5.1 : Canal Utilisateur

**Objectif** : Interface pour interaction avec l'utilisateur

**Actions** :
1. Créer `interfaces/` pour les canaux
2. Implémenter interface CLI ou API pour utilisateur
3. Connecter au noyau primaire et mémoire

**Structure** :
```
LIA/
└── interfaces/
    ├── __init__.py
    ├── user_channel.py         # Canal utilisateur
    └── tests/
        └── test_user_channel.py
```

**Critères de validation** :
- ✅ Utilisateur peut interagir avec LIA
- ✅ Interactions sont journalisées
- ✅ Réponses utilisent contexte mémoire

### Étape 5.2 : Canal Noyau d'Appui

**Objectif** : Canal d'échange avec le noyau d'appui (Gemini)

**Actions** :
1. Implémenter canal où LIA interroge Gemini
2. Intégrer dans le cycle d'apprentissage autonome
3. Tests

**Critères de validation** :
- ✅ LIA peut interroger Gemini via canal dédié
- ✅ Canal fonctionne dans autonomie
- ✅ Connaissances sont intégrées

---

## Phase 6 : Autonomie (Étape 6)

### Étape 6.1 : Scheduler Autonome

**Objectif** : Créer le scheduler pour autonomie

**Actions** :
1. Créer `autonomy/` pour l'autonomie
2. Implémenter scheduler de base
3. Intégrer avec noyau primaire et mémoire

**Structure** :
```
LIA/
└── autonomy/
    ├── __init__.py
    ├── scheduler.py            # Scheduler autonome
    ├── config.py               # Configuration autonomie
    └── tests/
        └── test_scheduler.py
```

**Critères de validation** :
- ✅ Scheduler tourne en arrière-plan
- ✅ Peut déclencher actions automatiques
- ✅ Intégration fonctionne

### Étape 6.2 : Auto-Apprentissage via Noyau d'Appui

**Objectif** : LIA apprend via Gemini dans son autonomie

**Actions** :
1. Intégrer interrogation Gemini dans scheduler
2. LIA choisit des sujets à explorer via Gemini
3. Connaissances apprises sont journalisées

**Critères de validation** :
- ✅ LIA interroge Gemini automatiquement
- ✅ Sujets sont choisis par LIA
- ✅ Connaissances sont journalisées

### Étape 6.3 : Objectifs Personnels

**Objectif** : Système d'objectifs personnels

**Actions** :
1. Ajouter modèle `PersonalGoal` dans mémoire
2. Intégrer avec scheduler
3. LIA peut créer ses propres objectifs

**Critères de validation** :
- ✅ Objectifs personnels fonctionnent
- ✅ LIA peut créer ses objectifs
- ✅ Scheduler déclenche objectifs

### Étape 6.4 : Contrôle Complet des Paramètres

**Objectif** : LIA peut modifier tous ses paramètres

**Actions** :
1. Créer système d'auto-modification des paramètres
2. LIA peut ajuster température, intervalles, etc.
3. Paramètres sont persistants

**Critères de validation** :
- ✅ LIA peut modifier tous ses paramètres
- ✅ Modifications sont persistantes
- ✅ Auto-calibration fonctionne

---

## Phase 7 : Validation et Tests (Étape 7)

### Étape 7.1 : Tests d'Intégration

**Objectif** : Valider l'ensemble du système

**Actions** :
1. Tests d'intégration complets
2. Validation de chaque composant
3. Validation des interactions entre composants

### Étape 7.2 : Documentation Complète

**Objectif** : Documenter le système final

**Actions** :
1. Documentation technique complète
2. Guide d'utilisation
3. Architecture finale

---

## Plan de Validation par Étape

### Critères Généraux de Validation

Chaque étape doit être validée avant de passer à la suivante :

1. **Fonctionnalité** : L'étape fonctionne comme prévu
2. **Tests** : Tests passent
3. **Documentation** : Documentation à jour
4. **Intégration** : Intégration avec étapes précédentes fonctionne
5. **Vision** : Aligné avec la vision clarifiée

### Processus de Validation

1. **Développement** : Implémenter l'étape
2. **Tests** : Écrire et exécuter tests
3. **Documentation** : Documenter l'étape
4. **Validation** : Vérifier critères
5. **Commit** : Commiter si validation OK
6. **Étape suivante** : Passer à l'étape suivante

---

## Structure Finale Cible

```
LIA/
├── README.md
├── .gitignore
├── config/
│   ├── api.conf.example
│   └── api.conf
├── docs/
│   ├── RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md
│   ├── ARCHITECTURE.md
│   ├── CONCEPTS.md
│   └── PLAN_REFONTE_PROJET.md
├── core/                        # Noyau primaire (Qwen2.5-1.5B-Instruct 4 bits)
│   ├── llm_adapter.py
│   ├── config.py
│   └── tests/
├── memory_service/              # Mémoire persistante
│   ├── models.py
│   ├── db.py
│   ├── api.py
│   └── tests/
├── support/                     # Noyaux d'appui
│   ├── gemini_adapter.py
│   ├── knowledge_source.py
│   └── tests/
├── interfaces/                  # Canaux d'interaction
│   ├── user_channel.py
│   └── tests/
├── autonomy/                    # Autonomie
│   ├── scheduler.py
│   ├── config.py
│   └── tests/
└── _archive/                    # Ancien code sauvegardé
```

---

## Prochaines Actions Immédiates

1. ✅ **Créer ce plan** (fait)
2. ⏳ **Créer dossier `_archive/`** et sauvegarder ancien code
3. ⏳ **Créer structure de base** (Phase 1)
4. ⏳ **Documenter vision clarifiée** (Phase 1)
5. ⏳ **Commencer Étape 2** (Noyau primaire)

---

## Notes Importantes

- **Pas de rush** : Prendre le temps de bien faire chaque étape
- **Validation obligatoire** : Ne pas passer à l'étape suivante sans validation
- **Documentation continue** : Documenter au fur et à mesure
- **Tests systématiques** : Tests à chaque étape
- **Vision claire** : Toujours se référer à la vision clarifiée

---

**Date de création** : 2024-12-19  
**Statut** : Plan créé, prêt à être exécuté

