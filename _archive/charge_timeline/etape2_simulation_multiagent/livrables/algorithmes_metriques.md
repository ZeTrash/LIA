# Algorithmes de calcul des métriques comportementales

## Vue d'ensemble

Les métriques comportementales sont calculées à partir des échanges multi-agents pour évaluer la variabilité, l'autonomie, la curiosité et la cohérence de LIA.

**Normalisation** : Toutes les métriques sont normalisées sur [0, 1] pour faciliter la comparaison et l'affichage.

## 1. Variabilité

**Objectif** : Mesurer la diversité des réponses et comportements.

### Formule

```
entropy_responses = -Σ(p_i * log2(p_i))
  où p_i = fréquence(response_i) / total_responses

diversity_topics = len(unique_topics) / max(1, total_topics_mentioned)

variability = (entropy_responses / max_entropy) * 0.6 + diversity_topics * 0.4
```

### Pseudo-code

```python
def calculate_variability(messages: List[Message]) -> float:
    # 1. Calculer l'entropie de Shannon sur les réponses
    response_counts = Counter(msg.content_hash for msg in messages)
    total = len(messages)
    entropy = 0.0
    max_entropy = log2(total) if total > 0 else 1.0
    
    for count in response_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * log2(p)
    
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    
    # 2. Calculer la diversité des sujets
    topics = set()
    for msg in messages:
        topics.update(extract_topics(msg.content))  # Extraction par mots-clés ou embedding
    
    diversity = len(topics) / max(1, len(messages) // 3)  # Normalisation approximative
    diversity = min(1.0, diversity)  # Capping à 1.0
    
    # 3. Combinaison pondérée
    variability = normalized_entropy * 0.6 + diversity * 0.4
    return min(1.0, max(0.0, variability))
```

### Paramètres

- **Poids entropie** : 0.6 (diversité des réponses)
- **Poids sujets** : 0.4 (diversité thématique)
- **Seuil minimum** : 0.0
- **Seuil maximum** : 1.0

## 2. Autonomie

**Objectif** : Mesurer la capacité à prendre des initiatives (vs simplement répondre).

### Formule

```
autonomy = (initiated_messages / total_messages) * 0.6 + (questions_count / total_messages) * 0.4
```

### Pseudo-code

```python
def calculate_autonomy(messages: List[Message], agent_id: str) -> float:
    agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
    total = len(agent_messages)
    
    if total == 0:
        return 0.0
    
    # 1. Compter les messages initiés (premier message d'un tour ou sans réponse directe)
    initiated = 0
    for i, msg in enumerate(agent_messages):
        if i == 0 or not is_direct_response(msg, agent_messages[i-1]):
            initiated += 1
    
    initiated_ratio = initiated / total
    
    # 2. Compter les questions
    questions = sum(1 for msg in agent_messages if is_question(msg.content))
    questions_ratio = questions / total
    
    # 3. Combinaison pondérée
    autonomy = initiated_ratio * 0.6 + questions_ratio * 0.4
    return min(1.0, max(0.0, autonomy))
```

### Paramètres

- **Poids initiation** : 0.6 (messages initiés)
- **Poids questions** : 0.4 (questions posées)
- **Détection question** : Regex `\?$` ou analyse syntaxique

## 3. Curiosité

**Objectif** : Mesurer la propension à explorer et questionner.

### Formule

```
curiosity = (questions_count / total_messages) * 0.5 + (new_topics / max(1, total_topics)) * 0.5
```

### Pseudo-code

```python
def calculate_curiosity(messages: List[Message], agent_id: str) -> float:
    agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
    total = len(agent_messages)
    
    if total == 0:
        return 0.0
    
    # 1. Compter les questions
    questions = sum(1 for msg in agent_messages if is_question(msg.content))
    questions_ratio = questions / total
    
    # 2. Calculer l'exploration de nouveaux sujets
    all_topics = set()
    new_topics_count = 0
    
    for msg in agent_messages:
        msg_topics = extract_topics(msg.content)
        new_topics = msg_topics - all_topics
        if new_topics:
            new_topics_count += len(new_topics)
        all_topics.update(msg_topics)
    
    total_topics = len(all_topics)
    exploration_ratio = new_topics_count / max(1, total_topics)
    
    # 3. Combinaison pondérée
    curiosity = questions_ratio * 0.5 + exploration_ratio * 0.5
    return min(1.0, max(0.0, curiosity))
```

### Paramètres

- **Poids questions** : 0.5
- **Poids exploration** : 0.5
- **Extraction topics** : Mots-clés (TF-IDF) ou embeddings (clustering)

## 4. Cohérence

**Objectif** : Mesurer la stabilité de la personnalité.

### Formule

```
coherence = mean(governance_scores.coherence) * 0.7 + (1 - trait_drift) * 0.3
```

### Pseudo-code

```python
def calculate_coherence(messages: List[Message], agent_id: str, initial_traits: Dict) -> float:
    agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
    
    if not agent_messages:
        return 0.0
    
    # 1. Score moyen de cohérence (via gouvernance)
    coherence_scores = [
        msg.metadata.scores.coherence 
        for msg in agent_messages 
        if msg.metadata and msg.metadata.scores
    ]
    
    if not coherence_scores:
        mean_coherence = 0.5  # Valeur par défaut
    else:
        mean_coherence = sum(coherence_scores) / len(coherence_scores)
    
    # 2. Calculer la dérive des traits
    # (Comparer les traits initiaux avec les traits finaux)
    final_traits = get_final_traits(agent_id)  # Récupérer depuis memory_service
    
    trait_drift = 0.0
    if initial_traits and final_traits:
        drift_scores = []
        for trait_id in initial_traits:
            if trait_id in final_traits:
                initial_value = initial_traits[trait_id].value
                final_value = final_traits[trait_id].value
                # Calculer distance (cosine similarity ou distance euclidienne normalisée)
                drift = calculate_trait_drift(initial_value, final_value)
                drift_scores.append(drift)
        
        if drift_scores:
            trait_drift = sum(drift_scores) / len(drift_scores)
    
    # 3. Combinaison pondérée
    coherence = mean_coherence * 0.7 + (1 - trait_drift) * 0.3
    return min(1.0, max(0.0, coherence))
```

### Paramètres

- **Poids cohérence gouvernance** : 0.7
- **Poids stabilité traits** : 0.3
- **Calcul drift trait** : Distance cosinus entre embeddings des valeurs

## 5. Agrégation et export

### Format d'export JSON

```json
{
  "session_id": "sim-20241207-001",
  "started_at": "2024-12-07T10:00:00Z",
  "ended_at": "2024-12-07T10:15:00Z",
  "agents": ["lia-primary", "lia-secondary"],
  "total_turns": 25,
  "metrics": {
    "variability": 0.78,
    "autonomy": 0.65,
    "curiosity": 0.82,
    "coherence": 0.91
  },
  "metrics_by_agent": {
    "lia-primary": {
      "variability": 0.75,
      "autonomy": 0.68,
      "curiosity": 0.80,
      "coherence": 0.92
    },
    "lia-secondary": {
      "variability": 0.81,
      "autonomy": 0.62,
      "curiosity": 0.84,
      "coherence": 0.90
    }
  },
  "messages": [...],
  "experiences_created": ["exp-sim-001"],
  "traits_updated": ["tone", "curiosity"]
}
```

### Calcul en temps réel vs batch

- **Temps réel** : Calcul incrémental après chaque message (approximation)
- **Batch** : Calcul complet à la fin de la simulation (précis)

**Recommandation** : Calcul batch pour précision, avec approximation temps réel pour dashboard.




