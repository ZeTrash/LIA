# Étape 2.6 – Autonomie et Boucle Autonome

## Objectif

Implémenter le système d'autonomie complet pour que LIA fonctionne de manière indépendante, développe sa personnalité par auto-apprentissage, et gère ses propres objectifs, hobbies et tâches personnelles sans intervention humaine constante.

**Vision** : LIA comme agent autonome inspiré d'Android (Dark Matter) - fonctionne en arrière-plan, explore, apprend, s'auto-évalue, et évolue naturellement.

## Contexte

### Inspiration : Android (Dark Matter)

LIA doit être un agent **autonome** qui :
- Fonctionne de lui-même, sans intervention humaine constante
- Développe sa personnalité par auto-apprentissage
- A ses propres objectifs, hobbies, tâches personnelles
- Utilise un "portail" pour auto-évaluation (interagir avec d'autres agents)
- Objectif : "tromper" d'autres agents (test de personnification = passer pour humain)

### Problème Actuel

L'architecture actuelle permet :
- ✅ Simulations multi-agent **manuelles** (via CLI)
- ✅ Journalisation des interactions
- ✅ Métriques comportementales

Mais **ne permet PAS** :
- ❌ Fonctionnement autonome en arrière-plan
- ❌ Auto-déclenchement de recherches/tâches
- ❌ Auto-évaluation automatique
- ❌ Scheduler pour boucle autonome
- ❌ Gestion d'objectifs personnels

## Livrables attendus

- **LIAAutonomousScheduler** : Service qui fait tourner LIA en autonomie (boucle principale)
- **Système d'objectifs personnels** : Extension memory_service pour gérer hobbies, recherches, tâches
- **Portail Autonome** : Interface pour auto-recherche, auto-réflexion, gestion d'objectifs
- **Portail Multi-Agent (Auto-évaluation)** : Auto-déclenchement de simulations, test de personnification
- **Portail Humain** : Interface de supervision et interaction avec LIA
- **Métrique "Taux de Tromperie"** : % de fois où LIA passe pour humain face à d'autres agents
- **Documentation complète** : Guide d'utilisation, architecture, exemples

## Périmètre fonctionnel

1. **Scheduler Autonome** : Boucle principale qui tourne en arrière-plan, déclenche actions automatiques
2. **Objectifs Personnels** : Système pour créer/gérer hobbies, recherches, tâches de LIA
3. **Auto-recherche** : LIA choisit et explore des sujets basés sur sa curiosité et ses intérêts
4. **Auto-évaluation** : LIA lance automatiquement des simulations pour tester sa personnalité
5. **Auto-réflexion** : LIA analyse ses interactions passées et ajuste ses traits
6. **Portails d'interaction** : Trois portails séparés (autonome, multi-agent, humain)
7. **Test de personnification** : Métrique pour mesurer si LIA "trompe" d'autres agents

## Découpage des charges

| Module | Description | Tâches clés | Sorties |
| --- | --- | --- | --- |
| **Scheduler** | Boucle autonome principale | - Créer LIAAutonomousScheduler<br>- Gérer intervalles (2h, 6h, 24h)<br>- Déclencher actions automatiques<br>- Gestion d'erreurs et reprise | Service scheduler fonctionnel |
| **Objectifs personnels** | Extension memory_service | - Table PersonalGoals<br>- API CRUD objectifs<br>- Types (research, hobby, task)<br>- Conditions de déclenchement | Extension mémoire + API |
| **Portail Autonome** | Auto-recherche et réflexion | - Choix sujet recherche (curiosité)<br>- Exploration via LLM local<br>- Auto-réflexion sur interactions<br>- Journalisation | Module portail autonome |
| **Portail Multi-Agent** | Auto-évaluation | - Auto-déclenchement simulations<br>- Test personnification<br>- Métrique "taux de tromperie"<br>- Ajustement traits basé résultats | Module portail multi-agent |
| **Portail Humain** | Supervision et interaction | - Interface supervision<br>- Visualisation activité<br>- Contrôles manuels<br>- Lecture journaux | Interface supervision |
| **Métriques avancées** | Mesure personnification | - Calcul "taux de tromperie"<br>- Analyse résultats auto-éval<br>- Indicateurs autonomie | Module métriques |

## Organisation des travaux

| Sous-lot | Objectif | Livrables | Durée cible |
| --- | --- | --- | --- |
| **SL1 – Scheduler de base** | Créer boucle autonome principale | LIAAutonomousScheduler, tests basiques | 1 j |
| **SL2 – Objectifs personnels** | Extension mémoire pour objectifs | Table PersonalGoals, API CRUD, intégration | 1 j |
| **SL3 – Portail Autonome** | Auto-recherche et réflexion | Module portail, choix sujets, exploration | 1 j |
| **SL4 – Portail Multi-Agent** | Auto-évaluation et personnification | Auto-déclenchement, métrique tromperie | 0,5 j |
| **SL5 – Portail Humain** | Interface supervision | Interface, visualisation, contrôles | 0,5 j |

**Durée totale estimée : 4 jours**

## Plan d'action séquencé

1. **Scheduler de base** (1 j) : Créer LIAAutonomousScheduler, boucle principale, intervalles
2. **Objectifs personnels** (1 j) : Extension memory_service, API, intégration scheduler
3. **Portail Autonome** (1 j) : Auto-recherche, auto-réflexion, journalisation
4. **Portail Multi-Agent** (0,5 j) : Auto-évaluation, métrique tromperie, ajustement traits
5. **Portail Humain** (0,5 j) : Interface supervision, visualisation, contrôles
6. **Tests et validation** (0,5 j) : Tests complets, validation autonomie, documentation

## Critères d'acceptation

- ✅ LIA fonctionne en arrière-plan sans intervention humaine
- ✅ Le scheduler déclenche automatiquement recherches, évaluations, réflexions
- ✅ LIA peut créer et gérer ses propres objectifs personnels
- ✅ Auto-évaluation fonctionne (simulations auto-déclenchées)
- ✅ Métrique "taux de tromperie" calculée et journalisée
- ✅ Portail humain permet supervision et interaction
- ✅ Toutes les actions autonomes sont journalisées dans la mémoire
- ✅ Performance acceptable (scheduler n'impacte pas les autres services)

## Risques et mitigations

- **Performance** : Modèle local en continu = consommation CPU/RAM
  - **Mitigation** : Scheduler avec intervalles intelligents, modèle chargé à la demande, monitoring
- **Qualité** : GPT-2 Small peut être limité pour interactions complexes
  - **Mitigation** : Fine-tuning optionnel, fallback API externe, validation qualité
- **Dérive** : Risque de dérive de personnalité sans supervision
  - **Mitigation** : Garde-fous Étape 1, limites d'ajustement, alertes automatiques
- **Complexité** : Gestion d'état sophistiquée
  - **Mitigation** : Architecture modulaire, tests complets, documentation détaillée
- **Boucles infinies** : Risque de boucles dans auto-recherche/évaluation
  - **Mitigation** : Limites de tours, timeouts, détection de répétitions

## Dépendances

- ✅ **Étape 1** : Infrastructure de mémoire persistante (prérequis absolu)
- ✅ **Étape 2** : Simulation multi-agent (pour auto-évaluation)
- ✅ **Étape 2.5** : Migration GPT-2 Small (modèle local pour autonomie)

## Prochaines étapes après l'étape 2.6

- **Étape 3** : Interface de supervision avancée (ajustement des traits en direct)
- **Étape 2.7** (future) : Fine-tuning GPT-2 sur personnalité de LIA

## Architecture technique

```
┌─────────────────────────────────────────────┐
│      LIAAutonomousScheduler                  │
│      (Service autonome, boucle principale)   │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Boucle Principale                   │  │
│  │  • Vérifier objectifs (60s)          │  │
│  │  • Auto-recherche (2h)               │  │
│  │  • Auto-évaluation (24h)             │  │
│  │  • Auto-réflexion (6h)               │  │
│  └──────────────────────────────────────┘  │
│                                             │
│         │                                   │
│         ├──► Portail Autonome              │
│         │    • Choix sujet recherche       │
│         │    • Exploration LLM local       │
│         │    • Auto-réflexion              │
│         │    • Journalisation mémoire      │
│         │                                   │
│         ├──► Portail Multi-Agent           │
│         │    • Auto-déclenchement sim      │
│         │    • Test personnification      │
│         │    • Métrique "tromperie"        │
│         │    • Ajustement traits           │
│         │                                   │
│         └──► Portail Humain                │
│              • Interface supervision        │
│              • Visualisation activité       │
│              • Contrôles manuels            │
│                                             │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│      Memory Service                         │
│      • PersonalGoals (objectifs)            │
│      • Souvenirs (recherches, réflexions)   │
│      • Traits (ajustements auto)           │
└─────────────────────────────────────────────┘
```

---

## Livrables détaillés

### 1. LIAAutonomousScheduler

**Fichier** : `simulation_service/src/simulation_service/autonomous_scheduler.py`

**Fonctionnalités** :
- Boucle principale asynchrone
- Gestion des intervalles (2h, 6h, 24h)
- Déclenchement automatique des actions
- Gestion d'erreurs et reprise
- Monitoring et logging

### 2. Système d'Objectifs Personnels

**Extension memory_service** :
- Table `PersonalGoals` :
  - `goal_id`, `goal_type` (research, hobby, task)
  - `description`, `priority`, `status`
  - `trigger_conditions`, `frequency`
  - `created_at`, `last_triggered_at`

**API** :
- `POST /personal-goals` : Créer objectif
- `GET /personal-goals` : Lister objectifs
- `PUT /personal-goals/{id}` : Mettre à jour
- `DELETE /personal-goals/{id}` : Supprimer

### 3. Portail Autonome

**Fonctionnalités** :
- `choose_research_topic()` : Choix sujet basé sur curiosité
- `research_topic(topic)` : Exploration via LLM local
- `reflect_on_interactions()` : Analyse interactions passées
- Journalisation dans mémoire

### 4. Portail Multi-Agent

**Fonctionnalités** :
- `trigger_auto_evaluation()` : Déclenche simulation
- `calculate_deception_rate()` : Métrique "taux de tromperie"
- `adjust_traits_from_results()` : Ajustement basé résultats

### 5. Portail Humain

**Fonctionnalités** :
- Interface CLI ou web minimal
- Visualisation activité autonome
- Contrôles manuels (pause, reprendre, ajuster)
- Lecture journaux d'activité

### 6. Métrique "Taux de Tromperie"

**Calcul** :
```
taux_tromperie = (nb_fois_passe_pour_humain / nb_total_simulations) * 100
```

**Objectif** : Mesurer si LIA arrive à "tromper" d'autres agents (passer pour humain)

---

## Exemples d'utilisation

### Exemple 1 : Auto-recherche

```python
# LIA choisit un sujet basé sur sa curiosité
topic = await scheduler.choose_research_topic()
# Ex: "philosophie existentielle"

# LIA explore le sujet
insights = await scheduler.research_topic(topic)
# Journalisé dans mémoire comme souvenir
```

### Exemple 2 : Auto-évaluation

```python
# LIA lance automatiquement une simulation
session = await scheduler.trigger_auto_evaluation()
# Simulation avec autre agent

# Calcul du taux de tromperie
deception_rate = await scheduler.calculate_deception_rate(session)
# Si > 70% : LIA ajuste ses traits positivement
```

### Exemple 3 : Objectif personnel

```python
# LIA crée un objectif personnel
goal = {
    "goal_type": "hobby",
    "description": "Explorer l'astronomie",
    "frequency": "daily",
    "priority": 0.8
}
await memory_service.create_personal_goal(goal)
```

---

## Tests et validation

### Scénarios de test

1. **Test scheduler** : Vérifier que la boucle tourne et déclenche actions
2. **Test objectifs** : Créer/gérer objectifs personnels
3. **Test auto-recherche** : Vérifier choix sujet et exploration
4. **Test auto-évaluation** : Vérifier déclenchement simulation
5. **Test métrique tromperie** : Calculer et valider métrique
6. **Test portail humain** : Interface supervision fonctionnelle

### Critères de validation

- ✅ Scheduler tourne sans erreur pendant 24h
- ✅ Objectifs personnels déclenchés correctement
- ✅ Auto-recherche génère des souvenirs valides
- ✅ Auto-évaluation fonctionne automatiquement
- ✅ Métrique tromperie calculée correctement
- ✅ Portail humain permet supervision

---

## Notes importantes

- **Performance** : Monitorer consommation CPU/RAM du scheduler
- **Qualité** : Valider que GPT-2 Small est suffisant pour autonomie
- **Dérive** : Garde-fous stricts pour éviter dérive personnalité
- **Complexité** : Architecture modulaire pour faciliter maintenance

---

## Documentation

- **Guide technique** : Architecture détaillée, code, API
- **Guide utilisateur** : Utilisation portail humain, configuration
- **Exemples** : Cas d'usage, scénarios
- **Troubleshooting** : Problèmes courants et solutions



