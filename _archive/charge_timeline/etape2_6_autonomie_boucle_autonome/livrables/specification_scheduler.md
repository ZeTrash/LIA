# Spécification LIAAutonomousScheduler

## Vue d'ensemble

`LIAAutonomousScheduler` est le service central qui fait tourner LIA en autonomie, déclenchant automatiquement recherches, évaluations et réflexions selon des intervalles configurés.

## Interface

### Classe LIAAutonomousScheduler

```python
class LIAAutonomousScheduler:
    """Scheduler qui fait tourner LIA en autonomie."""
    
    def __init__(
        self,
        memory_service: MemoryService,
        orchestrator: SimulationOrchestrator,
        local_llm: LocalLLMAdapter,
        config: AutonomousConfig
    ):
        """
        Initialise le scheduler autonome.
        
        Args:
            memory_service: Service mémoire (Étape 1)
            orchestrator: Orchestrateur simulation (Étape 2)
            local_llm: Adapter LLM local (Étape 2.5)
            config: Configuration du scheduler
        """
    
    async def start(self) -> None:
        """Démarre le scheduler (boucle principale)."""
    
    async def stop(self) -> None:
        """Arrête le scheduler proprement."""
    
    async def run_autonomous_loop(self) -> None:
        """Boucle principale d'autonomie."""
    
    async def check_personal_goals(self) -> None:
        """Vérifie et déclenche les objectifs personnels (intervalle: 60s)."""
    
    async def trigger_auto_research(self) -> None:
        """Déclenche une auto-recherche (intervalle: 2h)."""
    
    async def trigger_auto_evaluation(self) -> None:
        """Déclenche une auto-évaluation (intervalle: 24h)."""
    
    async def trigger_auto_reflection(self) -> None:
        """Déclenche une auto-réflexion (intervalle: 6h)."""
    
    def get_status(self) -> SchedulerStatus:
        """Retourne le statut actuel du scheduler."""
```

## Boucle principale

### Structure

```python
async def run_autonomous_loop(self):
    """Boucle principale d'autonomie."""
    while self.running:
        now = datetime.utcnow()
        
        # Vérifier objectifs personnels (toutes les 60s)
        if (now - self.last_goals_check).total_seconds() >= 60:
            await self.check_personal_goals()
            self.last_goals_check = now
        
        # Auto-recherche (toutes les 2h)
        if (now - self.last_research).total_seconds() >= 7200:  # 2h
            await self.trigger_auto_research()
            self.last_research = now
        
        # Auto-réflexion (toutes les 6h)
        if (now - self.last_reflection).total_seconds() >= 21600:  # 6h
            await self.trigger_auto_reflection()
            self.last_reflection = now
        
        # Auto-évaluation (toutes les 24h)
        if (now - self.last_evaluation).total_seconds() >= 86400:  # 24h
            await self.trigger_auto_evaluation()
            self.last_evaluation = now
        
        # Pause entre itérations
        await asyncio.sleep(10)  # Vérifier toutes les 10 secondes
```

## Intervalles configurables

| Action | Intervalle par défaut | Configurable | Description |
| --- | --- | --- | --- |
| Vérification objectifs | 60 secondes | Oui | Vérifie si des objectifs doivent être déclenchés |
| Auto-recherche | 2 heures | Oui | LIA choisit et explore un sujet |
| Auto-réflexion | 6 heures | Oui | LIA analyse ses interactions passées |
| Auto-évaluation | 24 heures | Oui | LIA lance une simulation multi-agent |

## Gestion des erreurs

### Erreurs temporaires

- **Timeout** : Action prend trop de temps → Logger, continuer boucle
- **Erreur API** : Erreur mémoire/service → Retry avec backoff, continuer
- **Erreur LLM** : Génération échoue → Fallback si configuré, continuer

### Erreurs critiques

- **Crash scheduler** : Exception non gérée → Arrêter scheduler, logger, notifier
- **Mémoire saturée** : RAM insuffisante → Arrêter temporairement, alerter

### Reprise automatique

- **Après erreur** : Attendre 5 minutes avant retry
- **Après crash** : Redémarrer automatiquement (max 3 fois/jour)

## Monitoring

### Métriques exposées

- `scheduler_uptime_seconds` : Temps de fonctionnement
- `actions_triggered_total` : Nombre total d'actions déclenchées
- `errors_count` : Nombre d'erreurs
- `last_research_at` : Dernière auto-recherche
- `last_evaluation_at` : Dernière auto-évaluation
- `last_reflection_at` : Dernière auto-réflexion

### Logging

- **Niveau INFO** : Actions déclenchées, intervalles respectés
- **Niveau WARNING** : Erreurs temporaires, retries
- **Niveau ERROR** : Erreurs critiques, crashes

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

## Performance

### Optimisations

- **Vérification légère** : Objectifs vérifiés toutes les 60s (pas de charge)
- **Actions asynchrones** : Toutes les actions en async (non-bloquant)
- **Cache** : Contexte mémoire mis en cache (5 min)
- **Limites** : Max 1 action à la fois (éviter surcharge)

### Limites

- **CPU** : < 10% en idle, < 50% pendant action
- **RAM** : < 100 MB supplémentaire (hors LLM)
- **Disque** : Logs limités à 100 MB (rotation)

## Sécurité

- **Isolation** : Scheduler isolé (pas d'accès direct à la DB)
- **Validation** : Toutes les actions validées avant exécution
- **Limites** : Limites strictes sur nombre d'actions/jour
- **Audit** : Toutes les actions journalisées
