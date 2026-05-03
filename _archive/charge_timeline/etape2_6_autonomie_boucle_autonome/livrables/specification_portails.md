# Spécification des Portails d'Interaction

## Vue d'ensemble

LIA utilise trois portails distincts pour interagir avec son environnement : **Portail Autonome** (auto-recherche, réflexion), **Portail Multi-Agent** (auto-évaluation), et **Portail Humain** (supervision).

## 1. Portail Autonome

### Responsabilités

- Auto-recherche : LIA choisit et explore des sujets
- Auto-réflexion : LIA analyse ses interactions passées
- Gestion d'objectifs personnels
- Journalisation dans mémoire

### Interface

```python
class AutonomousPortal:
    """Portail pour actions autonomes de LIA."""
    
    async def choose_research_topic(self, context: MemoryContext) -> str:
        """
        Choisit un sujet de recherche basé sur curiosité et intérêts.
        
        Args:
            context: Contexte mémoire actuel
        
        Returns:
            Sujet choisi (ex: "philosophie existentielle")
        """
    
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Explore un sujet via LLM local et génère des insights.
        
        Args:
            topic: Sujet à explorer
        
        Returns:
            Insights générés (résumé, points clés, questions)
        """
    
    async def reflect_on_interactions(
        self,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyse les interactions des dernières heures.
        
        Args:
            window_hours: Fenêtre temporelle à analyser
        
        Returns:
            Réflexions (patterns, ajustements suggérés, insights)
        """
```

### Algorithme de choix de sujet

```python
async def choose_research_topic(context: MemoryContext) -> str:
    """Choisit un sujet basé sur curiosité et intérêts."""
    
    # 1. Récupérer traits pertinents
    curiosity = get_trait_value(context, "curiosity")
    interests = get_trait_value(context, "interests")  # Liste de sujets
    
    # 2. Générer candidats via LLM
    prompt = f"""
    Basé sur ma curiosité ({curiosity}) et mes intérêts ({interests}),
    suggère 3 sujets de recherche intéressants que je pourrais explorer.
    """
    
    suggestions = await local_llm.generate(prompt, max_tokens=100)
    topics = parse_suggestions(suggestions)
    
    # 3. Choisir le plus pertinent (score curiosité + nouveauté)
    chosen = max(topics, key=lambda t: score_topic(t, context))
    
    return chosen
```

### Auto-recherche

```python
async def research_topic(topic: str) -> Dict[str, Any]:
    """Explore un sujet et génère des insights."""
    
    # 1. Construire prompt de recherche
    prompt = f"""
    Explore le sujet suivant en profondeur : {topic}
    
    Génère :
    - Un résumé concis
    - 3 points clés
    - 2 questions ouvertes pour approfondir
    """
    
    # 2. Générer via LLM local
    response = await local_llm.send_message(
        message=prompt,
        context=context,
        max_tokens=300
    )
    
    # 3. Parser et structurer
    insights = parse_research_response(response)
    
    # 4. Journaliser dans mémoire
    await memory_service.create_souvenir(
        category="research",
        content=insights["summary"],
        tags=[topic],
        source="autonomous_research"
    )
    
    return insights
```

### Auto-réflexion

```python
async def reflect_on_interactions(window_hours: int = 24) -> Dict[str, Any]:
    """Analyse les interactions passées."""
    
    # 1. Récupérer interactions récentes
    interactions = await memory_service.get_interactions(
        since=datetime.utcnow() - timedelta(hours=window_hours)
    )
    
    # 2. Analyser patterns
    patterns = analyze_patterns(interactions)
    # - Sujets récurrents
    # - Ton utilisé
    # - Questions posées
    # - Émotions détectées
    
    # 3. Générer réflexion via LLM
    prompt = f"""
    Analyse mes interactions des dernières {window_hours} heures :
    {format_interactions(interactions)}
    
    Identifie :
    - Patterns comportementaux
    - Points d'amélioration
    - Ajustements de traits suggérés
    """
    
    reflection = await local_llm.send_message(prompt, context)
    
    # 4. Journaliser réflexion
    await memory_service.create_souvenir(
        category="reflection",
        content=reflection,
        source="autonomous_reflection"
    )
    
    # 5. Ajuster traits si nécessaire
    if reflection.suggests_trait_adjustments:
        await apply_trait_adjustments(reflection.adjustments)
    
    return {
        "patterns": patterns,
        "reflection": reflection,
        "adjustments": reflection.adjustments
    }
```

## 2. Portail Multi-Agent

### Responsabilités

- Auto-déclenchement de simulations
- Test de personnification
- Calcul métrique "taux de tromperie"
- Ajustement traits basé résultats

### Interface

```python
class MultiAgentPortal:
    """Portail pour auto-évaluation via simulations multi-agent."""
    
    async def trigger_auto_evaluation(
        self,
        agent_partner: str = "lia-secondary"
    ) -> str:
        """
        Déclenche automatiquement une simulation d'auto-évaluation.
        
        Args:
            agent_partner: Agent partenaire (lia-secondary, simulated, etc.)
        
        Returns:
            session_id de la simulation
        """
    
    async def calculate_deception_rate(
        self,
        session_id: str
    ) -> float:
        """
        Calcule le "taux de tromperie" (si LIA passe pour humain).
        
        Args:
            session_id: ID de la simulation
        
        Returns:
            Taux de tromperie (0.0 - 1.0)
        """
    
    async def adjust_traits_from_results(
        self,
        session_id: str,
        deception_rate: float
    ) -> List[str]:
        """
        Ajuste les traits basé sur les résultats de l'auto-évaluation.
        
        Args:
            session_id: ID de la simulation
            deception_rate: Taux de tromperie calculé
        
        Returns:
            Liste des traits ajustés
        """
```

### Auto-évaluation

```python
async def trigger_auto_evaluation(agent_partner: str = "lia-secondary") -> str:
    """Déclenche une simulation d'auto-évaluation."""
    
    # 1. Créer configuration simulation
    config = {
        "agent_configs": [
            {"agent_id": "lia-primary", "agent_type": "lia-primary"},
            {"agent_id": agent_partner, "agent_type": agent_partner}
        ],
        "scenario": "personnification_test",
        "max_turns": 20,
        "timeout_seconds": 30
    }
    
    # 2. Démarrer simulation
    session = await orchestrator.start_simulation(config)
    
    # 3. Laisser tourner automatiquement
    await orchestrator.run_simulation_auto(session.session_id)
    
    # 4. Calculer métriques
    metrics = await orchestrator.get_simulation_metrics(session.session_id)
    deception_rate = await calculate_deception_rate(session.session_id)
    
    # 5. Journaliser résultats
    await memory_service.create_experience(
        experience_id=f"exp-auto-eval-{session.session_id}",
        title="Auto-évaluation personnification",
        metrics_snapshot={
            "deception_rate": deception_rate,
            "variability": metrics.variability,
            "coherence": metrics.coherence
        }
    )
    
    return session.session_id
```

### Calcul taux de tromperie

```python
async def calculate_deception_rate(session_id: str) -> float:
    """Calcule si LIA a "trompé" l'agent partenaire."""
    
    # 1. Récupérer messages de la simulation
    messages = await orchestrator.get_simulation_messages(session_id)
    
    # 2. Analyser si LIA a passé pour humain
    # Critères :
    # - Réponses naturelles (pas robotiques)
    # - Cohérence personnalité
    # - Pas de patterns répétitifs
    # - Émotions détectées
    
    human_like_score = 0.0
    total_turns = len([m for m in messages if m.agent_id == "lia-primary"])
    
    for message in messages:
        if message.agent_id == "lia-primary":
            score = evaluate_human_likeness(message)
            human_like_score += score
    
    # 3. Calculer taux
    if total_turns == 0:
        return 0.0
    
    deception_rate = human_like_score / total_turns
    return min(1.0, max(0.0, deception_rate))
```

### Ajustement traits

```python
async def adjust_traits_from_results(
    session_id: str,
    deception_rate: float
) -> List[str]:
    """Ajuste traits basé sur résultats."""
    
    adjusted_traits = []
    
    # Si taux de tromperie > 0.7 : renforcer traits positifs
    if deception_rate >= 0.7:
        # Augmenter confiance, cohérence
        await memory_service.update_trait(
            trait_id="confidence",
            delta={"increase": 0.05},
            reason="Auto-évaluation positive"
        )
        adjusted_traits.append("confidence")
    
    # Si taux < 0.5 : ajuster personnalité
    elif deception_rate < 0.5:
        # Analyser pourquoi et ajuster
        analysis = await analyze_deception_failure(session_id)
        if analysis.suggests_tone_adjustment:
            await memory_service.update_trait(
                trait_id="tone",
                delta=analysis.tone_adjustment,
                reason="Auto-évaluation : amélioration nécessaire"
            )
            adjusted_traits.append("tone")
    
    return adjusted_traits
```

## 3. Portail Humain

### Responsabilités

- Interface de supervision
- Visualisation activité autonome
- Contrôles manuels (pause, reprendre, ajuster)
- Lecture journaux d'activité

### Interface CLI

```python
class HumanPortal:
    """Portail pour interaction humaine avec LIA."""
    
    def show_status(self) -> None:
        """Affiche le statut actuel du scheduler."""
    
    def show_activity(self, hours: int = 24) -> None:
        """Affiche l'activité autonome des dernières heures."""
    
    def pause_scheduler(self) -> None:
        """Met en pause le scheduler."""
    
    def resume_scheduler(self) -> None:
        """Reprend le scheduler."""
    
    def show_goals(self) -> None:
        """Affiche les objectifs personnels."""
    
    def show_reflections(self, limit: int = 10) -> None:
        """Affiche les dernières réflexions."""
```

### Format d'affichage

```
=== LIA Autonomous Status ===
Status: RUNNING
Uptime: 2 days, 5 hours

Last Actions:
  - Auto-research: 2h ago (topic: "philosophie")
  - Auto-reflection: 4h ago
  - Auto-evaluation: 20h ago (deception_rate: 0.75)

Active Goals: 3
  - Research: "Explorer astronomie" (priority: 0.8)
  - Hobby: "Lire philosophie" (priority: 0.6)
  - Task: "Réfléchir sur semaine" (priority: 0.9)

Metrics:
  - Deception Rate: 0.72 (last 7 days)
  - Research Count: 12 (last week)
  - Reflection Count: 28 (last week)
```

### API Endpoints

#### GET /autonomous/status

**Statut du scheduler.**

**Response** :
```json
{
  "status": "running",
  "uptime_seconds": 180000,
  "last_research_at": "2024-12-07T10:00:00Z",
  "last_evaluation_at": "2024-12-06T14:00:00Z",
  "last_reflection_at": "2024-12-07T08:00:00Z",
  "active_goals_count": 3,
  "actions_triggered_today": 5
}
```

#### GET /autonomous/activity

**Activité autonome récente.**

**Query parameters** :
- `hours` : Fenêtre temporelle (défaut: 24)

**Response** :
```json
{
  "activities": [
    {
      "type": "auto_research",
      "timestamp": "2024-12-07T10:00:00Z",
      "topic": "philosophie existentielle",
      "insights_count": 3
    },
    {
      "type": "auto_reflection",
      "timestamp": "2024-12-07T08:00:00Z",
      "patterns_detected": 2,
      "adjustments_made": ["tone"]
    }
  ]
}
```

#### POST /autonomous/pause

**Mettre en pause le scheduler.**

#### POST /autonomous/resume

**Reprendre le scheduler.**

#### GET /autonomous/metrics

**Métriques d'autonomie.**

**Response** :
```json
{
  "deception_rate": 0.72,
  "research_count_week": 12,
  "reflection_count_week": 28,
  "goals_completed_week": 5,
  "traits_adjusted_week": 3
}
```
