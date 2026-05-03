# Architecture technique – Autonomie et Boucle Autonome

## Vue d'ensemble

Architecture complète pour permettre à LIA de fonctionner de manière autonome avec un scheduler central orchestrant trois portails d'interaction.

## Architecture système

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
│      • Traits (ajustements auto)          │
│      • Experiences (auto-évaluations)      │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│      Simulation Service                     │
│      • Orchestrator (simulations)          │
│      • LocalLLMAdapter (GPT-2)             │
└─────────────────────────────────────────────┘
```

## Composants principaux

### 1. LIAAutonomousScheduler

**Responsabilités** :
- Boucle principale asynchrone
- Gestion des intervalles (2h, 6h, 24h)
- Déclenchement automatique des actions
- Gestion d'erreurs et reprise
- Monitoring et logging

**Implémentation** :
- Classe `LIAAutonomousScheduler` dans `simulation_service/src/simulation_service/autonomous_scheduler.py`
- Boucle asynchrone avec `asyncio`
- État persistant (dernières actions, statut)

### 2. Système d'Objectifs Personnels

**Responsabilités** :
- Extension memory_service avec table `PersonalGoals`
- API CRUD pour objectifs
- Conditions de déclenchement
- Calcul `next_trigger_at`

**Implémentation** :
- Table SQL `personal_goals`
- Modèle `PersonalGoalModel` dans `memory_service/models.py`
- Endpoints API dans `memory_service/api.py`

### 3. Portail Autonome

**Responsabilités** :
- Choix sujet de recherche (basé curiosité)
- Exploration via LLM local
- Auto-réflexion sur interactions
- Journalisation dans mémoire

**Implémentation** :
- Classe `AutonomousPortal` dans `simulation_service/portals/autonomous.py`
- Intégration avec `LocalLLMAdapter`
- Intégration avec `memory_service`

### 4. Portail Multi-Agent

**Responsabilités** :
- Auto-déclenchement simulations
- Test de personnification
- Calcul métrique "taux de tromperie"
- Ajustement traits basé résultats

**Implémentation** :
- Classe `MultiAgentPortal` dans `simulation_service/portals/multi_agent.py`
- Intégration avec `SimulationOrchestrator`
- Algorithmes de calcul métriques

### 5. Portail Humain

**Responsabilités** :
- Interface supervision (CLI ou web)
- Visualisation activité
- Contrôles manuels
- Lecture journaux

**Implémentation** :
- Classe `HumanPortal` dans `simulation_service/portals/human.py`
- CLI avec `rich` ou `click`
- Endpoints API pour supervision

## Flux d'exécution

### Démarrage du scheduler

```
1. Initialiser LIAAutonomousScheduler
   ↓
2. Charger configuration (intervalles, etc.)
   ↓
3. Récupérer état persistant (dernières actions)
   ↓
4. Démarrer boucle principale (run_autonomous_loop)
   ↓
5. Scheduler tourne en arrière-plan
```

### Boucle principale

```
1. Vérifier objectifs personnels (toutes les 60s)
   ↓
2. Si objectif à déclencher → Exécuter via portail approprié
   ↓
3. Vérifier auto-recherche (toutes les 2h)
   ↓
4. Si temps écoulé → Déclencher auto-recherche
   ↓
5. Vérifier auto-réflexion (toutes les 6h)
   ↓
6. Si temps écoulé → Déclencher auto-réflexion
   ↓
7. Vérifier auto-évaluation (toutes les 24h)
   ↓
8. Si temps écoulé → Déclencher auto-évaluation
   ↓
9. Pause 10 secondes → Retour étape 1
```

### Auto-recherche

```
1. Portail Autonome : choose_research_topic()
   ↓
2. Générer candidats via LLM local
   ↓
3. Choisir sujet (score curiosité + nouveauté)
   ↓
4. Portail Autonome : research_topic(topic)
   ↓
5. Explorer sujet via LLM local
   ↓
6. Générer insights (résumé, points clés, questions)
   ↓
7. Journaliser dans mémoire (Souvenir category="research")
   ↓
8. Mettre à jour last_research
```

### Auto-évaluation

```
1. Portail Multi-Agent : trigger_auto_evaluation()
   ↓
2. Créer configuration simulation (lia-primary ↔ agent-partner)
   ↓
3. Démarrer simulation automatiquement
   ↓
4. Laisser tourner (max 20 tours)
   ↓
5. Calculer métriques (variabilité, cohérence, etc.)
   ↓
6. Calculer taux de tromperie
   ↓
7. Ajuster traits si nécessaire
   ↓
8. Journaliser Experience dans mémoire
   ↓
9. Mettre à jour last_evaluation
```

## Gestion des erreurs

### Erreurs temporaires

- **Timeout action** : Logger, continuer boucle
- **Erreur LLM** : Fallback si configuré, continuer
- **Erreur mémoire** : Retry avec backoff, continuer

### Erreurs critiques

- **Crash scheduler** : Arrêter, logger, notifier
- **Mémoire saturée** : Arrêter temporairement, alerter

### Reprise automatique

- **Après erreur** : Attendre 5 min avant retry
- **Après crash** : Redémarrer (max 3 fois/jour)

## Performance

### Optimisations

- **Vérification légère** : Objectifs toutes les 60s (pas de charge)
- **Actions asynchrones** : Toutes les actions non-bloquantes
- **Cache contexte** : Contexte mémoire mis en cache (5 min)
- **Limites** : Max 1 action à la fois

### Limites

- **CPU** : < 10% en idle, < 50% pendant action
- **RAM** : < 100 MB supplémentaire (hors LLM)
- **Disque** : Logs limités à 100 MB (rotation)

## Configuration

### Fichier de configuration

```yaml
autonomous_scheduler:
  enabled: true
  intervals:
    goals_check_seconds: 60
    auto_research_hours: 2
    auto_reflection_hours: 6
    auto_evaluation_hours: 24
  error_handling:
    max_retries: 3
    retry_delay_seconds: 300
    auto_restart: true
  monitoring:
    log_level: "INFO"
    metrics_enabled: true
```

### Variables d'environnement

```bash
LIA_AUTONOMOUS_ENABLED=true
LIA_AUTONOMOUS_INTERVAL_RESEARCH_HOURS=2
LIA_AUTONOMOUS_INTERVAL_REFLECTION_HOURS=6
LIA_AUTONOMOUS_INTERVAL_EVALUATION_HOURS=24
```

## Déploiement

### Local

```bash
# Démarrer scheduler
python -m simulation_service.autonomous_scheduler

# Ou via service
uvicorn simulation_service.api:app --port 4700
# Scheduler démarre automatiquement si configuré
```

### Production

- **Service système** : systemd ou supervisor
- **Docker** : Container avec scheduler en arrière-plan
- **Monitoring** : Métriques exposées (Prometheus)

## Sécurité

- **Isolation** : Scheduler isolé (pas d'accès direct DB)
- **Validation** : Toutes les actions validées
- **Limites** : Limites strictes sur actions/jour
- **Audit** : Toutes les actions journalisées
