# Concepts Clés de LIA

**Version** : 0.1.0  
**Date** : 2024-12-19

---

## Vue d'Ensemble

Ce document définit les concepts fondamentaux de LIA, clarifiés lors de la refonte du projet.

---

## 1. Noyau Primaire vs Noyau d'Appui

### Noyau Primaire

**Définition** : Moteur de génération de réponses

**Rôle** :
- Générer des réponses à partir de prompts
- Utiliser le contexte mémoire pour personnaliser les réponses
- Gérer les paramètres de génération

**Implémentation** :Qwen2.5-1.5B-Instruct 4 bits (modèle local léger)

**Important** : Le noyau primaire n'est **PAS** la source de connaissance, c'est le moteur de génération.

### Noyau d'Appui

**Définition** : Première source de connaissance (comme un livre)

**Rôle** :
- Fournir des informations et connaissances
- Servir de support externe de connaissances
- Permettre à LIA d'apprendre et d'explorer

**Implémentation** : Gemini API (source externe)

**Important** : Le noyau d'appui est la **première source de connaissance**, pas le moteur de génération.

### Distinction Clé

```
Noyau Primaire (Qwen2.5-1.5B-Instruct 4 bits)     ≠     Noyau d'Appui (Gemini)
Moteur de génération              Source de connaissance
Comment répondre                  Quoi apprendre
```

---

## 2. Noyaux d'Appui vs Noyaux Secondaires

### Concept Unifié

**Noyaux d'Appui** = **Noyaux Secondaires** (même concept)

### Différence : Local vs API

#### Noyau d'Appui Local

**Définition** : Support cognitif direct

**Caractéristiques** :
- Modèle local (ex: Llama, Mistral)
- Support cognitif direct
- Traitement local des informations

**Utilisation** : Aucun au début du projet

#### Noyau d'Appui API

**Définition** : Source d'informations à la manière d'un livre

**Caractéristiques** :
- API externe (ex: Gemini)
- Source d'informations
- Consultation comme un livre

**Utilisation** : Gemini au début du projet

### Résumé

```
Noyaux d'Appui / Noyaux Secondaires
├── Local → Support cognitif direct
└── API → Source d'infos comme livre (ex: Gemini)
```

---

## 3. Canaux d'Interaction

### Canal Utilisateur

**Définition** : Interface pour interaction avec l'utilisateur

**Rôle** :
- Permettre à l'utilisateur d'interagir avec LIA
- Visualiser l'activité autonome
- Superviser et ajuster

**Implémentation** : CLI ou API REST

### Canal Noyau d'Appui

**Définition** : Canal d'échange avec le noyau d'appui (Gemini)

**Rôle** :
- Permettre à LIA d'interroger Gemini pour apprendre
- Intégrer dans le cycle d'apprentissage autonome
- Journaliser les connaissances apprises

**Implémentation** : Interface dédiée pour interrogation Gemini

### Distinction

```
Canal Utilisateur          Canal Noyau d'Appui
Interaction humaine        LIA interroge Gemini
Supervision                Auto-apprentissage
```

---

## 4. Contrôle Complet des Paramètres

### Définition

LIA peut modifier et ajuster **tous** ses paramètres.

### Paramètres Contrôlables

1. **Paramètres de génération** :
   - Température
   - Max length
   - Top-p, Top-k
   - Repetition penalty

2. **Paramètres de scheduler** :
   - Intervalles (recherche, réflexion, évaluation)
   - Fréquences d'objectifs
   - Timeouts

3. **Paramètres de gouvernance** :
   - Seuils de scoring
   - Limites de dérive
   - TTL des souvenirs

4. **Traits de personnalité** :
   - Valeurs, ton, style
   - Poids, confiance

5. **Objectifs personnels** :
   - Priorités
   - Fréquences
   - Conditions de déclenchement

### Auto-Calibration

LIA peut s'auto-adapter et se calibrer en modifiant ces paramètres selon ses expériences.

---

## 5. Mémoire Persistante

### Définition

Base de données locale représentant la mémoire de l'agent.

### Contenu

1. **Traits** : Personnalité, valeurs, ton, compétences
2. **Souvenirs** : Faits, préférences, alertes
3. **Interactions** : Logs de toutes les interactions
4. **Objectifs** : Objectifs personnels de LIA
5. **Expériences** : Agrégations d'interactions

### Rôle

- **Personnalité** : Stockage des traits évolutifs
- **Contexte** : Fourniture du contexte pour génération
- **Apprentissage** : Journalisation des apprentissages
- **Évolution** : Traçabilité de l'évolution

---

## 6. Autonomie

### Définition

Capacité de LIA à fonctionner de manière indépendante, sans intervention humaine constante.

### Composants

1. **Scheduler** : Boucle autonome principale
2. **Objectifs personnels** : Hobbies, recherches, tâches
3. **Auto-recherche** : Exploration via noyau d'appui
4. **Auto-évaluation** : Évaluation de sa personnalité
5. **Auto-réflexion** : Analyse de ses interactions

### Cycle d'Autonomie

```
Scheduler
    ↓
Vérification objectifs
    ↓
Auto-recherche (si nécessaire)
    ↓
Auto-réflexion (si nécessaire)
    ↓
Auto-évaluation (si nécessaire)
    ↓
Journalisation
    ↓
Mise à jour personnalité
    ↓
Boucle suivante
```

---

## 7. Cycle d'Évolution

### Concept

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

### Explication

1. **Désirs** : Ce que LIA veut faire/explorer
2. **Rêves** : Vision de ce qu'elle pourrait devenir
3. **Objectifs** : Buts concrets à atteindre
4. **Compétences** : Capacités nécessaires
5. **Apprentissages** : Acquisition des compétences
6. **Expériences** : Mise en pratique
7. **Nouveaux désirs** : Émergence de nouveaux désirs

### Dynamique Continue

Ce cycle forme une **dynamique d'évolution continue** où LIA grandit et évolue naturellement.

---

## 8. Apprentissage

### Phases

#### Phase 1 : Imitation

- Observer, reproduire
- Suivre les repères fournis
- Apprendre par immersion

#### Phase 2 : Autodidaxie

- Questions personnelles
- Recherche autonome de réponses
- Exploration, imagination

### Sources d'Apprentissage

1. **Interactions utilisateur** : Échanges directs
2. **Noyau d'appui** : Interrogation Gemini
3. **Auto-recherche** : Exploration autonome
4. **Auto-réflexion** : Analyse des interactions
5. **Expériences** : Mise en pratique

### Futur

- Exploration web
- Réseaux sociaux agents
- Médias, culture, jeux

---

## 9. Personnalité Évolutive

### Définition

Personnalité qui évolue et se transforme au fil des expériences.

### Composants

1. **Traits** : Caractéristiques de personnalité
2. **Valeurs** : Ce qui est important pour LIA
3. **Ton** : Manière de s'exprimer
4. **Compétences** : Capacités acquises
5. **Préférences** : Goûts et intérêts

### Évolution

- **Initiale** : Traits de base
- **Par expérience** : Ajustement selon interactions
- **Par auto-apprentissage** : Évolution autonome
- **Par réflexion** : Analyse et ajustement

### Gouvernance

- Contrôle de dérive
- Scoring et filtrage
- Versioning des traits
- Limites et garde-fous

---

## 10. Inspiration : Android (Dark Matter)

### Concept

Agent autonome en quête d'identité, d'émotions et de compréhension du monde.

### Similarités avec LIA

- **Autonomie** : Fonctionne de manière indépendante
- **Personnalité évolutive** : Se transforme au fil du temps
- **Objectifs personnels** : A ses propres buts
- **Auto-évaluation** : Réflexion sur soi
- **Interaction** : Avec utilisateur et autres agents

### Différences

- **Corps physique** : Android a un corps, LIA est virtuel
- **Conscience** : Android (fiction) vs LIA (illusion statistique)
- **Apprentissage** : Android (expériences réelles) vs LIA (interactions simulées)

---

## Résumé des Concepts

| Concept | Définition | Exemple |
|---------|-----------|---------|
| **Noyau Primaire** | Moteur de génération | Qwen2.5-1.5B-Instruct 4 bits |
| **Noyau d'Appui** | Source de connaissance | Gemini API |
| **Mémoire** | Base de données locale | SQLite/PostgreSQL |
| **Canal Utilisateur** | Interface utilisateur | CLI/API REST |
| **Canal Noyau d'Appui** | Interface Gemini | API dédiée |
| **Autonomie** | Fonctionnement indépendant | Scheduler |
| **Contrôle Complet** | Modification de tous paramètres | Auto-calibration |
| **Personnalité Évolutive** | Personnalité qui change | Traits versionnés |

---

## Références

- **Vision** : `docs/RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md`
- **Architecture** : `docs/ARCHITECTURE.md`
- **Plan de refonte** : `docs/PLAN_REFONTE_PROJET.md`

---

**Date de création** : 2024-12-19  
**Dernière mise à jour** : 2024-12-19

