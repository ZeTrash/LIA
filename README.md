# LIA - Laboratoire d'Intelligence Artificielle

**Version** : 0.1.0 (Refonte)  
**Date** : 2024-12-19

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

### Vue d'Ensemble

```
┌─────────────────────────────────────────┐
│              LIA Agent                   │
├─────────────────────────────────────────┤
│  Noyau Primaire : GPT-2 (génération)   │
│  Noyau d'Appui : Gemini (connaissance)  │
│  Mémoire : Base de données locale       │
│  Canaux : Utilisateur, Noyau d'appui   │
│  Autonomie : Scheduler, objectifs       │
└─────────────────────────────────────────┘
```

### Composants

- **`core/`** : Noyau primaire (GPT-2) - Moteur de génération
- **`support/`** : Noyau d'appui (Gemini) - Première source de connaissance
- **`memory_service/`** : Mémoire persistante - Personnalité et souvenirs
- **`interfaces/`** : Canaux d'interaction - Utilisateur et noyau d'appui
- **`autonomy/`** : Système d'autonomie - Scheduler et objectifs personnels

### Concepts Clés

- **Noyau primaire** (GPT-2) = Moteur de génération
- **Noyau d'appui** (Gemini) = Première source de connaissance (comme un livre)
- **Mémoire** = Base de données locale (personnalité, souvenirs)
- **Contrôle complet** = LIA peut modifier tous ses paramètres

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
├── core/                        # Noyau primaire (GPT-2)
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

### ⏳ Phase 2 : Noyau Primaire (GPT-2)

**Statut** : À venir

- Intégration GPT-2 comme moteur de génération
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

- Python 3.9+
- pip
- (Optionnel) PostgreSQL pour la production

### Configuration

1. Copier le fichier de configuration :
```bash
cp config/api.conf.example config/api.conf
```

2. Éditer `config/api.conf` avec vos paramètres (clé API Gemini)

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
**Dernière mise à jour** : 2024-12-19
