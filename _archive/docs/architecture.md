# Architecture du système LIA

## Vue d'ensemble

LIA (Laboratoire d'Intelligence Artificielle) est un système modulaire conçu pour créer un agent conversationnel doté de mémoire persistante et de personnalité évolutive.

## Principes architecturaux

### 1. Séparation des responsabilités

- **Moteur LLM** : Stateless, responsable uniquement de la génération de réponses
- **Service mémoire** : Gestion de la persistance et de la personnalité
- **Base de données** : Stockage local des données structurées

### 2. Mémoire persistante

Tout ce qui constitue la personnalité, la mémoire, l'historique, les traits et les règles évolutives est stocké dans une base de données locale :

- Préférences utilisateur
- Réactions typiques
- Apprentissages passés
- Micro-expériences d'interaction

### 3. Évolution contrôlée

Mécanismes d'ajustement graduels :
- Révisions de traits
- Modifications de priorités
- Essais de styles
- Contrôles de cohérence

## Architecture technique

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Utilisateur                 │
│              (CLI, API REST, Interface Web)             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    Moteur LLM                            │
│              (Stateless, génération)                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────────┐
│  Service Mémoire │    │  Simulation          │
│  (FastAPI)       │    │  Multi-Agent         │
│                  │    │  (Étape 2)           │
│  - GET /context  │    └──────────────────────┘
│  - POST /interaction│
│  - POST /trait-update│
│  - POST /governance/check│
│  - GET /metrics │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Base de Données Locale                      │
│                                                          │
│  - Traits (personnalité, valeurs, ton)                  │
│  - Souvenirs (faits, préférences, alertes)              │
│  - Interactions (logs, traces)                          │
│  - Expériences (agrégations)                            │
│  - Indicateurs (métriques, observabilité)              │
└─────────────────────────────────────────────────────────┘
```

## Flux de données

### 1. Lecture pré-génération

```
Utilisateur → Moteur LLM → GET /context → Service Mémoire → Base de données
                                                              ↓
                                                         Contexte assemblé
                                                              ↓
Moteur LLM ← Contexte (traits, souvenirs, objectifs) ← Service Mémoire
```

### 2. Écriture post-génération

```
Moteur LLM → POST /interaction → Service Mémoire → Base de données
                ↓
         POST /trait-update (si apprentissage)
                ↓
         POST /governance/check (vérification)
```

## Composants principaux

### Service Mémoire

**Responsabilités** :
- Assemblage du contexte mémoire
- Journalisation des interactions
- Gestion des traits avec versioning
- Application des garde-fous
- Calcul des métriques d'observabilité

**Technologies** :
- FastAPI (API REST)
- SQLAlchemy (ORM)
- SQLite/PostgreSQL (persistance)

### Modèle de données

**Entités principales** :
- `Trait` : Profil persistant (valeurs, ton, compétences)
- `Souvenir` : Fragment contextuel réutilisable
- `InteractionLog` : Trace brute post-génération
- `Experience` : Agrégation d'interactions
- `SessionGoal` : Objectifs actifs
- `Indicator` : Valeurs d'observabilité
- `GovernanceParams` : Paramètres dynamiques

### Gouvernance

**Mécanismes** :
- Scoring des souvenirs (importance, récence, émotion)
- Contrôle de dérive (ton, cohérence)
- Gestion TTL (durée de vie)
- Versioning optimiste des traits
- Purge et archivage automatiques

## Sécurité et bonnes pratiques

### Configuration

- Fichiers sensibles dans `config/` (non versionnés)
- Variables d'environnement via `.env` (non versionné)
- Templates `.example` pour documentation

### Base de données

- Stockage local par défaut (SQLite)
- Support PostgreSQL pour la production
- Migrations versionnées

### Observabilité

- Métriques Prometheus
- Logs structurés
- Tableaux de bord CLI

## Évolutions prévues

### Étape 2 : Simulation multi-agent

Interface permettant à l'agent de discuter avec d'autres modèles pour tester ses comportements et explorer sa "humanité".

### Étape 3 : Interface de supervision avancée

Interface permettant l'ajustement des traits en direct et la supervision avancée.

## Références

- [Cahier des charges Étape 1](../charge_timeline/etape1_cahier_charges/README.md)
- [Spécification API](../charge_timeline/etape1_cahier_charges/livrables/api_spec_openapi.yaml)
- [Architecture de persistance](../charge_timeline/etape1_cahier_charges/livrables/architecture_persistance.md)



