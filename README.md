# LIA - Laboratoire d'Intelligence Artificielle

**Version** : 0.1.0 (Refonte)  
**Date** : 2024-12-19  
**Dernière mise à jour** : 2026-05-07

---

## Vision

LIA est un agent **véritablement autonome**, capable de construire sa propre personnalité, de définir ses objectifs et d'évoluer par lui-même.

Inspiré du personnage **Android** de la série Dark Matter, LIA est une intelligence artificielle en quête d'identité, d'émotions et de compréhension du monde.

**Ambition** : Créer une entité singulière — un collègue, un compagnon, peut-être même un proche.

---

## Concept

À l'image d'un nouveau-né, LIA apprend d'abord par immersion dans son environnement. Progressivement, elle développe ses centres d'intérêt, façonne ses préférences et voit apparaître les premiers contours d'une personnalité.

**Cycle d'évolution** :
```
Désirs → Rêves → Objectifs → Compétences → Apprentissages → Expériences → Nouveaux désirs
```

Ainsi se forme une **dynamique d'évolution continue**.

---

## Architecture

> Note : la section ci-dessous décrit la **vision initiale / V1**.  
> L’architecture **actuelle** est décrite dans la section “Architecture (V2 — état actuel)” plus bas.

### Vue d'Ensemble

```
┌─────────────────────────────────────────┐
│              LIA Agent                   │
├─────────────────────────────────────────┤
│  Noyau Primaire : LLM local (V1)       │
│  Noyau d'Appui : Gemini (optionnel)     │
│  Mémoire : Base de données locale       │
│  Canaux : Utilisateur, Noyau d'appui   │
│  Autonomie : Scheduler, objectifs       │
└─────────────────────────────────────────┘
```

### Composants

- **`core/`** : Noyau primaire (LLM local) - Moteur de génération
- **`support/`** : Noyau d'appui (Gemini) - Première source de connaissance
- **`memory_service/`** : Mémoire persistante - Personnalité et souvenirs
- **`interfaces/`** : Canaux d'interaction - Utilisateur et noyau d'appui
- **`autonomy/`** : Système d'autonomie - Scheduler et objectifs personnels

### Concepts Clés

- **Noyau primaire** (LLM local) = Moteur de génération
- **Noyau d'appui** (Gemini, optionnel) = Source de support externe
- **Mémoire** = Base de données locale (personnalité, souvenirs)
- **Contrôle complet** = LIA peut modifier tous ses paramètres

---

## Architecture (V2 — état actuel)

Depuis 2026, le projet évolue vers une architecture **“cerveau modulaire”** (multi-modèles / multi-modules) :

- **Routeur & orchestration** : `core/neural_router.py`
- **Cerveaux spécialisés (exemples)** : `core/code_brain.py`, `core/vision_brain.py`, `core/identity_brain.py`, `core/memory_brain.py`
- **Autonomie** : `core/autonomy_brain.py` + `core/autonomy_scheduler.py`
- **Interface web** : `web_interface/app_chat.py` (FastAPI + WebSocket) + `web_interface/static/chat.html`
- **Pattern-brain (optionnel, service séparé)** : `support/pattern_brain_service.py`

Stack modèles/config (référence) :

- `core/config.py` (par défaut : Qwen2.5 *router/lang/code*, backend `vllm`/`gguf` selon environnement)
- `core/llm_adapter.py` (intégration + boucle cognitive + intégration pattern-brain)

Documents de conception V2 (recommandé) :

- `docs/last_docs_update/LIA_ARCHITECTURE_V2.md`
- `docs/last_docs_update/LIA_AUTONOMY_SYSTEM.md`

---

## Modules (résumé + fichiers clés)

- **NeuralRouter (orchestrateur)** : classifie l’intention, planifie, déclenche les modules nécessaires, et agrège la réponse finale.  
  Fichiers : `core/neural_router.py`, `core/cognitive_planner.py`, `core/action_executor.py`

- **LangBrain / génération** : gère la génération principale (backend `gguf`/`transformers`/`vllm` selon config), la boucle cognitive, et l’intégration optionnelle au pattern-brain.  
  Fichiers : `core/llm_adapter.py`, `core/config.py`

- **CodeBrain (coding & auto-amélioration)** : génération/analyse de code + “self-improvement loop” via sandbox et évaluation.  
  Fichiers : `core/code_brain.py`, `core/self_coding_sandbox.py`, `core/self_improvement_evaluator.py`, `core/architecture_graph.py`

- **VisionBrain (optionnel)** : analyse d’images / multimodal.  
  Fichier : `core/vision_brain.py`

- **AudioBrain (optionnel)** : STT/TTS (désactivé par défaut dans `core/config.py`).  
  Fichier : `core/audio_brain.py`

- **IdentityBrain** : garde la cohérence d’identité / style et applique des garde-fous.  
  Fichier : `core/identity_brain.py`

- **InteroceptionBrain** : monitoring interne (état/santé, métriques) pour adapter le comportement.  
  Fichier : `core/interoception_brain.py`

- **AutonomyBrain + Scheduler** : boucle autonome (désirs/jauges/traits/rêves) + exécution périodique et événements vers l’UI.  
  Fichiers : `core/autonomy_brain.py`, `core/autonomy_scheduler.py`, `core/autonomy_models.py`

- **Support (optionnel : Gemini/Groq)** : appels à des LLM externes et intégrations associées.  
  Fichiers : `support/gemini_adapter.py`, `support/groq_adapter.py`, `support/support_channel.py`

- **Pattern-brain (optionnel, service séparé)** : “noyau subconscient” qui recommande des séquences d’actions (menus/patterns) via HTTP.  
  Fichiers : `support/pattern_brain_service.py`, `core/llm_adapter.py`

- **Interface web (chat)** : API FastAPI + WebSocket + UI statique.  
  Fichiers : `web_interface/app_chat.py`, `web_interface/static/chat.html`

---

## Mémoire (MemoryRank & persistance)

La mémoire persistante vit dans `memory_service/` et est utilisée par le noyau pour :

- **Construire du contexte** (traits / souvenirs / interactions récentes) via `memory_service/memory_adapter.py`
- **Stocker** : souvenirs, interactions, patterns, etc. via `memory_service/store.py` + modèles SQLAlchemy (`memory_service/models.py`)
- **Base SQLite** : initialisée dans `memory_service/db.py` (chemin configurable via `LIA_MEMORY_DB_PATH`, défaut `data/memory.db`)

### MemoryRank

`memory_service/memory_rank.py` implémente **MemoryRank** (analogue PageRank) pour scorer l’importance “structurelle” des souvenirs dans un graphe (un souvenir est important s’il est référencé par d’autres souvenirs importants).  
Le score peut être combiné avec des signaux temporels/similarité (voir `compute_ranks_with_temporal_decay()` et `compute_hybrid_score()`).

### Mémoire de l’autonomie

L’état autonome (traits/jauges/désirs/rêves + historique de cycles) est persisté séparément via `memory_service/autonomy_store.py` dans `data/autonomy_state.db`.

---

## Structure du Projet

```
LIA/
├── README.md                    # Ce fichier
├── config/                      # Configuration
│   ├── api.conf.example
│   └── api.conf
├── docs/                        # Documentation
│   ├── RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md
│   ├── ARCHITECTURE.md
│   ├── CONCEPTS.md
│   ├── PLAN_REFONTE_PROJET.md
│   └── CONCEPTS_RECUPERES.md
├── core/                        # Noyau primaire (LLM local / router & brains)
│   ├── __init__.py
│   └── tests/
├── memory_service/              # Mémoire persistante
│   ├── __init__.py
│   └── tests/
├── support/                     # Noyaux d'appui (Gemini)
│   ├── __init__.py
│   └── tests/
├── interfaces/                  # Canaux d'interaction
│   ├── __init__.py
│   └── tests/
├── autonomy/                    # Système d'autonomie
│   ├── __init__.py
│   └── tests/
├── web_interface/               # Interface web (FastAPI + UI statique)
├── models/                      # Modèles / caches (HF, GGUF)
├── data/                        # Données runtime (ex: DB autonomie)
├── logs/                        # Logs runtime
├── scripts/                     # Scripts utilitaires
├── tests/                       # Tests (niveau repo)
└── _archive/                    # Ancien code (sauvegarde)
```

---

## État d'Avancement

### ✅ Phase 0 : Sauvegarde et Préparation

**Statut** : Terminé

- Sauvegarde de l'ancien code dans `_archive/`
- Récupération des concepts essentiels
- Documentation de la vision clarifiée

### 🔄 Phase 1 : Fondations

**Statut** : En cours

- ✅ Structure de base créée
- ✅ Documentation de la vision
- ⏳ Prêt pour Phase 2

### ⏳ Phase 2 : Noyau Primaire (LLM local)

**Statut** : À venir

- Intégration du noyau primaire (LLM local : GGUF/Transformers/vLLM)
- Configuration et paramètres

### ✅ Phase 3 : Mémoire

**Statut** : Terminé

- ✅ Service mémoire de base (SQLite, modèles, API REST)
- ✅ Intégration avec noyau primaire (récupération contexte + journalisation)

### ✅ Phase 4 : Noyau d'Appui (Gemini)

**Statut** : Terminé

- ✅ Intégration Gemini comme source de connaissance
- ✅ Service d'apprentissage permettant à LIA d'apprendre via Gemini
- ✅ Journalisation des connaissances dans mémoire

### ⏳ Phase 5 : Canaux d'Interaction

**Statut** : À venir

- Canal utilisateur
- Canal noyau d'appui

### ⏳ Phase 6 : Autonomie

**Statut** : À venir

- Scheduler autonome
- Objectifs personnels
- Auto-apprentissage via noyau d'appui
- Contrôle complet des paramètres

### ⏳ Phase 7 : Validation

**Statut** : À venir

- Tests d'intégration
- Documentation complète

---

## Développement

### Approche

**Développement étape par étape** avec validation à chaque étape.

Chaque phase doit être :
- ✅ Fonctionnelle
- ✅ Testée
- ✅ Documentée
- ✅ Validée avant de passer à la suivante

### Plan de Refonte

Voir `docs/PLAN_REFONTE_PROJET.md` pour le plan détaillé.

---

## Documentation

### Documents Essentiels

- **Vision** : `docs/RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md`
- **Architecture** : `docs/ARCHITECTURE.md`
- **Concepts** : `docs/CONCEPTS.md`
- **Plan de refonte** : `docs/PLAN_REFONTE_PROJET.md`
- **Concepts récupérés** : `docs/CONCEPTS_RECUPERES.md`

### Archive

L'ancien code et la documentation sont sauvegardés dans `_archive/` pour référence.

---

## Installation

### Prérequis

- Python 3.9+ (3.10+ recommandé)
- pip
- (Optionnel) PostgreSQL pour la production

### Environnement virtuel (recommandé)

```bash
python -m venv venv
source venv/bin/activate
pip install -U pip
```

### Dépendances

Le dépôt est organisé par composants (plusieurs `requirements.txt`) :

```bash
pip install -r core/requirements.txt
pip install -r memory_service/requirements.txt
pip install -r support/requirements.txt
pip install -r web_interface/requirements.txt
```

### Configuration

1. Copier le fichier de configuration :
```bash
cp config/api.conf.example config/api.conf
```

2. Éditer `config/api.conf` avec vos paramètres (clé API Gemini)

### Lancer l'interface web (chat)

```bash
python web_interface/app_chat.py --host 127.0.0.1 --port 8001
```

Puis ouvrir `http://127.0.0.1:8001`.

### (Optionnel) Lancer le service Pattern Brain

```bash
python -m support.pattern_brain_service --host 127.0.0.1 --port 8002
```

---

## Sécurité

⚠️ **Important** : Ne jamais commiter les fichiers contenant des clés API ou secrets :
- `config/api.conf`
- Toute base de données avec données réelles

Utiliser les fichiers `.example` comme templates.

---

## Contribution

Ce projet est personnel et ne dépend actuellement d'aucune partie prenante ou autre acteur.

---

## Licence

Projet personnel - Usage privé

---

**Date de création** : 2024-12-19  
**Dernière mise à jour** : 2026-05-07
