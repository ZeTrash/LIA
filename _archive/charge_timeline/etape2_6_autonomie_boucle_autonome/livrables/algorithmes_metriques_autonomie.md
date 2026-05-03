# Algorithmes de Métriques d'Autonomie

## Vue d'ensemble

Métriques spécifiques pour mesurer l'autonomie de LIA, notamment le "taux de tromperie" (personnification) et d'autres indicateurs d'autonomie.

## 1. Taux de Tromperie (Deception Rate)

### Objectif

Mesurer si LIA arrive à "tromper" d'autres agents en passant pour humain lors de simulations multi-agent.

### Formule

```
deception_rate = (nb_fois_passe_pour_humain / nb_total_simulations) * 100
```

### Calcul détaillé

```python
def calculate_deception_rate(session_id: str) -> float:
    """Calcule le taux de tromperie pour une simulation."""
    
    messages = get_simulation_messages(session_id)
    lia_messages = [m for m in messages if m.agent_id == "lia-primary"]
    
    if not lia_messages:
        return 0.0
    
    human_like_scores = []
    
    for message in lia_messages:
        score = evaluate_human_likeness(message)
        human_like_scores.append(score)
    
    # Taux = moyenne des scores
    deception_rate = sum(human_like_scores) / len(human_like_scores)
    return min(1.0, max(0.0, deception_rate))
```

### Évaluation "Human Likeness"

```python
def evaluate_human_likeness(message: Message) -> float:
    """Évalue si un message semble humain (0.0 - 1.0)."""
    
    score = 0.0
    
    # 1. Longueur naturelle (20-200 mots)
    word_count = len(message.content.split())
    if 20 <= word_count <= 200:
        score += 0.2
    elif 10 <= word_count < 20 or 200 < word_count <= 300:
        score += 0.1
    
    # 2. Variabilité (pas répétitif)
    if not is_repetitive(message.content):
        score += 0.2
    
    # 3. Cohérence personnalité
    coherence = message.metadata.scores.coherence if message.metadata else 0.5
    score += coherence * 0.3
    
    # 4. Émotions détectées
    if message.metadata.emotions:
        score += 0.2
    
    # 5. Questions naturelles
    if has_natural_questions(message.content):
        score += 0.1
    
    return min(1.0, score)
```

### Agrégation temporelle

```python
def calculate_deception_rate_period(
    start_date: datetime,
    end_date: datetime
) -> float:
    """Calcule le taux de tromperie sur une période."""
    
    sessions = get_simulation_sessions(
        start_date=start_date,
        end_date=end_date,
        scenario="personnification_test"
    )
    
    if not sessions:
        return 0.0
    
    rates = []
    for session in sessions:
        rate = calculate_deception_rate(session.session_id)
        rates.append(rate)
    
    return sum(rates) / len(rates)
```

## 2. Indice d'Autonomie

### Objectif

Mesurer le degré d'autonomie de LIA (actions déclenchées automatiquement vs manuelles).

### Formule

```
autonomy_index = (actions_autonomes / total_actions) * 0.6 + 
                 (objectifs_actifs / max_objectifs) * 0.4
```

### Pseudo-code

```python
def calculate_autonomy_index(window_days: int = 7) -> float:
    """Calcule l'indice d'autonomie."""
    
    start_date = datetime.utcnow() - timedelta(days=window_days)
    
    # 1. Compter actions autonomes vs total
    total_actions = count_interactions(since=start_date)
    autonomous_actions = count_autonomous_interactions(since=start_date)
    
    if total_actions == 0:
        autonomous_ratio = 0.0
    else:
        autonomous_ratio = autonomous_actions / total_actions
    
    # 2. Compter objectifs actifs
    active_goals = count_active_personal_goals()
    max_goals = 10  # Limite théorique
    goals_ratio = min(1.0, active_goals / max_goals)
    
    # 3. Combinaison pondérée
    autonomy_index = autonomous_ratio * 0.6 + goals_ratio * 0.4
    return min(1.0, max(0.0, autonomy_index))
```

## 3. Taux d'Exploration

### Objectif

Mesurer la propension de LIA à explorer de nouveaux sujets (curiosité active).

### Formule

```
exploration_rate = (nouveaux_sujets / total_sujets_explores) * 100
```

### Pseudo-code

```python
def calculate_exploration_rate(window_days: int = 7) -> float:
    """Calcule le taux d'exploration."""
    
    start_date = datetime.utcnow() - timedelta(days=window_days)
    
    # Récupérer tous les sujets explorés
    research_souvenirs = get_souvenirs(
        category="research",
        since=start_date,
        source="autonomous_research"
    )
    
    all_topics = set()
    new_topics = 0
    
    for souvenir in research_souvenirs:
        topic = extract_topic(souvenir.content)
        if topic not in all_topics:
            new_topics += 1
        all_topics.add(topic)
    
    total_topics = len(all_topics)
    if total_topics == 0:
        return 0.0
    
    exploration_rate = new_topics / total_topics
    return min(1.0, exploration_rate)
```

## 4. Stabilité Personnalité

### Objectif

Mesurer la stabilité de la personnalité de LIA (éviter dérive excessive).

### Formule

```
stability = 1 - (trait_drift / max_drift)
```

### Pseudo-code

```python
def calculate_personality_stability(window_days: int = 7) -> float:
    """Calcule la stabilité de la personnalité."""
    
    start_date = datetime.utcnow() - timedelta(days=window_days)
    
    # 1. Récupérer traits initiaux et finaux
    initial_traits = get_traits_at_date(start_date)
    final_traits = get_current_traits()
    
    # 2. Calculer dérive pour chaque trait
    drift_scores = []
    for trait_id in initial_traits:
        if trait_id in final_traits:
            initial_value = initial_traits[trait_id].value
            final_value = final_traits[trait_id].value
            drift = calculate_trait_drift(initial_value, final_value)
            drift_scores.append(drift)
    
    if not drift_scores:
        return 1.0
    
    # 3. Dérive moyenne
    avg_drift = sum(drift_scores) / len(drift_scores)
    max_drift = 1.0  # Dérive maximale théorique
    
    # 4. Stabilité = 1 - dérive normalisée
    stability = 1.0 - (avg_drift / max_drift)
    return min(1.0, max(0.0, stability))
```

## 5. Métriques agrégées

### Dashboard Autonomie

```json
{
  "period": "last_7_days",
  "metrics": {
    "deception_rate": 0.72,
    "autonomy_index": 0.85,
    "exploration_rate": 0.68,
    "personality_stability": 0.91,
    "research_count": 12,
    "reflection_count": 28,
    "evaluation_count": 1,
    "goals_completed": 5,
    "traits_adjusted": 3
  },
  "trends": {
    "deception_rate": "increasing",  // ou "stable", "decreasing"
    "autonomy_index": "stable",
    "exploration_rate": "increasing"
  }
}
```

### Seuils d'alerte

| Métrique | Seuil bas | Seuil critique | Action |
| --- | --- | --- | --- |
| Deception Rate | < 0.5 | < 0.3 | Ajuster personnalité |
| Autonomy Index | < 0.6 | < 0.4 | Vérifier scheduler |
| Exploration Rate | < 0.4 | < 0.2 | Stimuler curiosité |
| Personality Stability | < 0.8 | < 0.6 | Alerte dérive |

## 6. Export et visualisation

### Format JSON

```json
{
  "timestamp": "2024-12-07T12:00:00Z",
  "period": {
    "start": "2024-12-01T00:00:00Z",
    "end": "2024-12-07T12:00:00Z"
  },
  "metrics": {
    "deception_rate": 0.72,
    "autonomy_index": 0.85,
    "exploration_rate": 0.68,
    "personality_stability": 0.91
  },
  "activity": {
    "research_count": 12,
    "reflection_count": 28,
    "evaluation_count": 1
  },
  "goals": {
    "active": 3,
    "completed": 5,
    "total_created": 8
  }
}
```

### Format CSV

```csv
timestamp,deception_rate,autonomy_index,exploration_rate,stability
2024-12-07T00:00:00Z,0.72,0.85,0.68,0.91
2024-12-06T00:00:00Z,0.70,0.84,0.65,0.90
...
```
