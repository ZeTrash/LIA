# Spécification Système d'Objectifs Personnels

## Vue d'ensemble

Extension de `memory_service` pour gérer les objectifs personnels de LIA (hobbies, recherches, tâches) qui peuvent être déclenchés automatiquement par le scheduler.

## Modèle de données

### Table PersonalGoals

```sql
CREATE TABLE personal_goals (
  goal_id TEXT PRIMARY KEY,
  goal_type TEXT NOT NULL CHECK (goal_type IN ('research', 'hobby', 'task')),
  description TEXT NOT NULL,
  priority REAL NOT NULL CHECK (priority BETWEEN 0 AND 1),
  status TEXT NOT NULL CHECK (status IN ('active', 'paused', 'completed', 'archived')),
  trigger_conditions JSON,
  frequency TEXT NOT NULL CHECK (frequency IN ('once', 'daily', 'weekly', 'monthly')),
  created_at TEXT NOT NULL,
  last_triggered_at TEXT,
  next_trigger_at TEXT,
  metadata JSON
);
```

### Schéma Pydantic

```python
class PersonalGoal(BaseModel):
    goal_id: str
    goal_type: Literal["research", "hobby", "task"]
    description: str
    priority: float  # 0.0 - 1.0
    status: Literal["active", "paused", "completed", "archived"]
    trigger_conditions: Dict[str, Any] | None
    frequency: Literal["once", "daily", "weekly", "monthly"]
    created_at: datetime
    last_triggered_at: datetime | None
    next_trigger_at: datetime | None
    metadata: Dict[str, Any] | None
```

## Types d'objectifs

### Research (Recherche)

**Description** : Sujet à explorer via auto-recherche.

**Exemple** :
```json
{
  "goal_type": "research",
  "description": "Explorer la philosophie existentielle",
  "priority": 0.8,
  "frequency": "weekly",
  "trigger_conditions": {
    "curiosity_threshold": 0.7
  }
}
```

### Hobby (Passe-temps)

**Description** : Activité récurrente que LIA apprécie.

**Exemple** :
```json
{
  "goal_type": "hobby",
  "description": "Lire sur l'astronomie",
  "priority": 0.6,
  "frequency": "daily",
  "trigger_conditions": {
    "time_of_day": "evening"
  }
}
```

### Task (Tâche)

**Description** : Tâche ponctuelle ou récurrente.

**Exemple** :
```json
{
  "goal_type": "task",
  "description": "Réfléchir sur les interactions de la semaine",
  "priority": 0.9,
  "frequency": "weekly",
  "trigger_conditions": {
    "day_of_week": "sunday"
  }
}
```

## API Endpoints

### POST /personal-goals

**Créer un objectif personnel.**

**Request** :
```json
{
  "goal_type": "research",
  "description": "Explorer la philosophie",
  "priority": 0.8,
  "frequency": "weekly",
  "trigger_conditions": {}
}
```

**Response** :
```json
{
  "goal_id": "goal-20241207-001",
  "goal_type": "research",
  "description": "Explorer la philosophie",
  "priority": 0.8,
  "status": "active",
  "frequency": "weekly",
  "created_at": "2024-12-07T10:00:00Z",
  "next_trigger_at": "2024-12-14T10:00:00Z"
}
```

### GET /personal-goals

**Lister les objectifs personnels.**

**Query parameters** :
- `status` : Filtrer par statut (active, paused, completed)
- `goal_type` : Filtrer par type (research, hobby, task)
- `priority_min` : Priorité minimum

**Response** :
```json
{
  "goals": [
    {
      "goal_id": "goal-001",
      "goal_type": "research",
      "description": "...",
      "priority": 0.8,
      "status": "active"
    }
  ],
  "total": 1
}
```

### GET /personal-goals/{goal_id}

**Détails d'un objectif.**

**Response** :
```json
{
  "goal_id": "goal-001",
  "goal_type": "research",
  "description": "...",
  "priority": 0.8,
  "status": "active",
  "frequency": "weekly",
  "created_at": "2024-12-07T10:00:00Z",
  "last_triggered_at": "2024-12-07T12:00:00Z",
  "next_trigger_at": "2024-12-14T10:00:00Z"
}
```

### PUT /personal-goals/{goal_id}

**Mettre à jour un objectif.**

**Request** :
```json
{
  "priority": 0.9,
  "status": "paused"
}
```

### DELETE /personal-goals/{goal_id}

**Supprimer un objectif (archivage).**

**Response** : 204 No Content

## Conditions de déclenchement

### Format trigger_conditions

```json
{
  "curiosity_threshold": 0.7,  // Seuil de curiosité
  "time_of_day": "evening",    // Moment de la journée
  "day_of_week": "sunday",     // Jour de la semaine
  "interaction_count": 10,     // Nombre d'interactions
  "trait_value": {              // Valeur de trait spécifique
    "trait_id": "curiosity",
    "min_value": 0.8
  }
}
```

### Logique de déclenchement

```python
def should_trigger_goal(goal: PersonalGoal, context: MemoryContext) -> bool:
    """Détermine si un objectif doit être déclenché."""
    
    # Vérifier fréquence
    if goal.frequency == "once" and goal.last_triggered_at:
        return False
    
    if goal.next_trigger_at and datetime.utcnow() < goal.next_trigger_at:
        return False
    
    # Vérifier conditions
    conditions = goal.trigger_conditions or {}
    
    if "curiosity_threshold" in conditions:
        curiosity = get_trait_value(context, "curiosity")
        if curiosity < conditions["curiosity_threshold"]:
            return False
    
    if "time_of_day" in conditions:
        current_hour = datetime.utcnow().hour
        if conditions["time_of_day"] == "evening" and current_hour < 18:
            return False
    
    # Toutes les conditions remplies
    return True
```

## Calcul next_trigger_at

```python
def calculate_next_trigger(goal: PersonalGoal) -> datetime:
    """Calcule la prochaine date de déclenchement."""
    now = datetime.utcnow()
    
    if goal.frequency == "once":
        return None  # Pas de prochain déclenchement
    
    if goal.frequency == "daily":
        return now + timedelta(days=1)
    
    if goal.frequency == "weekly":
        return now + timedelta(weeks=1)
    
    if goal.frequency == "monthly":
        return now + timedelta(days=30)
    
    return None
```

## Intégration avec scheduler

Le scheduler vérifie les objectifs toutes les 60 secondes :

```python
async def check_personal_goals(self):
    """Vérifie et déclenche les objectifs personnels."""
    goals = await self.memory_service.get_active_personal_goals()
    context = await self.memory_service.get_context(session_id="autonomous")
    
    for goal in goals:
        if should_trigger_goal(goal, context):
            await self.execute_goal(goal)
            await self.memory_service.update_personal_goal(
                goal.goal_id,
                last_triggered_at=datetime.utcnow(),
                next_trigger_at=calculate_next_trigger(goal)
            )
```

## Exemples d'utilisation

### Créer un objectif de recherche

```python
goal = {
    "goal_type": "research",
    "description": "Explorer la philosophie existentielle",
    "priority": 0.8,
    "frequency": "weekly",
    "trigger_conditions": {
        "curiosity_threshold": 0.7
    }
}
await memory_service.create_personal_goal(goal)
```

### Créer un hobby

```python
goal = {
    "goal_type": "hobby",
    "description": "Lire sur l'astronomie",
    "priority": 0.6,
    "frequency": "daily",
    "trigger_conditions": {
        "time_of_day": "evening"
    }
}
await memory_service.create_personal_goal(goal)
```
