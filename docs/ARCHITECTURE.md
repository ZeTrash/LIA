# Architecture de LIA

**Version** : 0.1.0  
**Date** : 2024-12-19  
**Statut** : Architecture cible clarifiée

---

## Vue d'Ensemble

LIA (Laboratoire d'Intelligence Artificielle) est un agent autonome capable de construire sa propre personnalité, de définir ses objectifs et d'évoluer par lui-même.

---

## Architecture Cible

```
┌─────────────────────────────────────────────────────────┐
│                    LIA Agent                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Noyau Primaire (core/)                          │  │
│  │  Qwen2.5-1.5B-Instruct 4 bits (léger, moteur de génération)             │  │
│  │  • Génération de réponses                        │  │
│  │  • Contrôle complet des paramètres               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Noyau d'Appui (support/)                         │  │
│  │  Gemini API (première source de connaissance)     │  │
│  │  • Source d'informations (comme un livre)        │  │
│  │  • Support externe de connaissances              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Mémoire (memory_service/)                        │  │
│  │  Base de données locale                          │  │
│  │  • Personnalité (traits)                         │  │
│  │  • Souvenirs                                     │  │
│  │  • Interactions                                  │  │
│  │  • Objectifs personnels                          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Canaux d'Interaction (interfaces/)             │  │
│  │  • Canal Utilisateur                             │  │
│  │  • Canal Noyau d'Appui (Gemini)                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Autonomie (autonomy/)                            │  │
│  │  • Scheduler autonome                            │  │
│  │  • Objectifs personnels                          │  │
│  │  • Auto-recherche, auto-évaluation, réflexion   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Composants Principaux

### 1. Noyau Primaire (`core/`)

**Rôle** : Moteur de génération de réponses

**Responsabilités** :
- Génération de réponses avec Qwen2.5-1.5B-Instruct 4 bits
- Construction de prompts avec contexte mémoire
- Gestion des paramètres de génération (température, max_length, etc.)
- Contrôle complet des paramètres (modifiables par LIA)

**Technologies** :
- Qwen2.5-1.5B-Instruct 4 bits (124M paramètres)
- Transformers (Hugging Face)
- PyTorch
- Quantisation INT4/INT8 (optionnel)

**Interface** :
```python
class LLMAdapter:
    async def generate(
        self,
        message: str,
        context: Dict[str, Any],
        session_id: str
    ) -> str:
        """Génère une réponse avec le contexte mémoire."""
        pass
```

---

### 2. Noyau d'Appui (`support/`)

**Rôle** : Première source de connaissance (comme un livre)

**Responsabilités** :
- Fournir des informations via Gemini API
- Servir de support externe de connaissances
- Permettre à LIA d'apprendre et d'explorer

**Technologies** :
- Gemini API (Google)
- HTTP client (httpx)

**Interface** :
```python
class KnowledgeSource:
    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Interroge la source de connaissance."""
        pass
```

**Distinction importante** :
- **Noyau primaire** (Qwen2.5-1.5B-Instruct 4 bits) = Moteur de génération
- **Noyau d'appui** (Gemini) = Source de connaissance (comme un livre)

---

### 3. Mémoire (`memory_service/`)

**Rôle** : Persistance de la personnalité et des souvenirs

**Responsabilités** :
- Stockage des traits de personnalité
- Stockage des souvenirs (faits, préférences, alertes)
- Journalisation des interactions
- Gestion des objectifs personnels
- Système de gouvernance (scoring, dérive, TTL)

**Technologies** :
- SQLite (développement)
- PostgreSQL (production)
- SQLAlchemy (ORM)
- FastAPI (API REST)

**Modèles de données** :
- `Trait` : Traits de personnalité (versionnés)
- `Souvenir` : Souvenirs/Mémoires (avec scores)
- `Interaction` : Logs d'interactions
- `PersonalGoal` : Objectifs personnels
- `Experience` : Agrégations d'interactions

**API REST** :
- `GET /context` : Récupération du contexte
- `POST /interaction` : Journalisation
- `POST /trait-update` : Mise à jour trait
- `POST /personal-goals` : Création objectif
- `GET /personal-goals` : Liste objectifs

---

### 4. Canaux d'Interaction (`interfaces/`)

**Rôle** : Interfaces pour les différents canaux d'interaction

#### Canal Utilisateur

**Responsabilités** :
- Interface pour interaction avec l'utilisateur
- CLI ou API REST
- Visualisation de l'activité autonome
- Supervision et ajustements

#### Canal Noyau d'Appui

**Responsabilités** :
- Canal d'échange avec Gemini
- Permettre à LIA d'interroger Gemini pour apprendre
- Intégration dans le cycle d'apprentissage autonome

**Distinction** :
- **Canal Utilisateur** : Interaction humaine avec LIA
- **Canal Noyau d'Appui** : LIA interroge Gemini pour apprendre

---

### 5. Autonomie (`autonomy/`)

**Rôle** : Système d'autonomie et d'auto-apprentissage

**Responsabilités** :
- Scheduler autonome (boucle principale)
- Gestion des objectifs personnels
- Auto-recherche (via noyau d'appui)
- Auto-évaluation
- Auto-réflexion
- Contrôle complet des paramètres

**Composants** :
- `Scheduler` : Boucle autonome principale
- `PersonalGoals` : Gestion des objectifs
- `AutoResearch` : Auto-recherche via Gemini
- `AutoEvaluation` : Auto-évaluation
- `AutoReflection` : Auto-réflexion

**Intervalles** (configurables) :
- Objectifs personnels : 60s
- Auto-recherche : 2h
- Auto-réflexion : 6h
- Auto-évaluation : 24h

---

## Flux de Données

### 1. Génération de Réponse (Canal Utilisateur)

```
Utilisateur
    ↓
Canal Utilisateur
    ↓
Noyau Primaire (Qwen2.5-1.5B-Instruct 4 bits)
    ↓
Mémoire (GET /context)
    ↓
Noyau Primaire (construction prompt)
    ↓
Génération réponse
    ↓
Mémoire (POST /interaction)
    ↓
Utilisateur
```

### 2. Auto-Apprentissage (Canal Noyau d'Appui)

```
Scheduler Autonome
    ↓
Auto-recherche (choix sujet)
    ↓
Canal Noyau d'Appui
    ↓
Noyau d'Appui (Gemini API)
    ↓
Connaissances reçues
    ↓
Mémoire (journalisation)
    ↓
Mise à jour personnalité
```

### 3. Cycle d'Évolution

```
Désirs
    ↓
Rêves
    ↓
Objectifs
    ↓
Compétences
    ↓
Apprentissages
    ↓
Expériences
    ↓
Nouveaux désirs
```

---

## Principes Architecturaux

### 1. Séparation des Responsabilités

- **Noyau primaire** : Génération uniquement
- **Noyau d'appui** : Source de connaissance
- **Mémoire** : Persistance uniquement
- **Canaux** : Interfaces d'interaction
- **Autonomie** : Orchestration autonome

### 2. Contrôle Complet

LIA peut modifier **tous** ses paramètres :
- Paramètres de génération (température, max_length)
- Intervalles de scheduler
- Métriques de gouvernance
- Traits de personnalité
- Objectifs personnels

### 3. Modularité

- Chaque composant est indépendant
- Interfaces claires entre composants
- Facilite l'ajout de nouveaux noyaux d'appui
- Facilite le remplacement du noyau primaire

### 4. Autonomie

- Fonctionnement en arrière-plan
- Auto-déclenchement des actions
- Auto-apprentissage via noyau d'appui
- Auto-évolution de la personnalité

---

## Structure des Dossiers

```
LIA/
├── core/                      # Noyau primaire (Qwen2.5-1.5B-Instruct 4 bits)
│   ├── __init__.py
│   ├── llm_adapter.py
│   ├── config.py
│   └── tests/
├── memory_service/            # Mémoire persistante
│   ├── __init__.py
│   ├── models.py
│   ├── db.py
│   ├── api.py
│   └── tests/
├── support/                   # Noyaux d'appui
│   ├── __init__.py
│   ├── gemini_adapter.py
│   ├── knowledge_source.py
│   └── tests/
├── interfaces/                # Canaux d'interaction
│   ├── __init__.py
│   ├── user_channel.py
│   ├── support_channel.py
│   └── tests/
├── autonomy/                  # Autonomie
│   ├── __init__.py
│   ├── scheduler.py
│   ├── config.py
│   └── tests/
├── config/                    # Configuration
│   ├── api.conf.example
│   └── api.conf
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   ├── CONCEPTS.md
│   └── ...
└── _archive/                  # Ancien code (sauvegarde)
```

---

## Évolutions Futures

### Noyaux Secondaires

**Concept** : Noyaux d'appui supplémentaires (locaux ou API)

**Types** :
- **Local** : Support cognitif direct (modèle local comme support)
- **API** : Source d'informations comme livre (comme Gemini)

**Utilisation** : Aucun au début du projet, mais architecture prête

### Exploration Web

**Fonctionnalité future** : Accès aux outils d'exploration du web

### Réseaux Sociaux Agents

**Fonctionnalité future** : Interactions avec réseaux sociaux dédiés aux agents

---

## Références

- **Vision** : `docs/RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md`
- **Concepts** : `docs/CONCEPTS.md`
- **Plan de refonte** : `docs/PLAN_REFONTE_PROJET.md`
- **Concepts récupérés** : `docs/CONCEPTS_RECUPERES.md`

---

**Date de création** : 2024-12-19  
**Dernière mise à jour** : 2024-12-19

