# Architecture Détaillée - Étape 2.6

## Vue d'ensemble

L'architecture de l'autonomie repose sur un **scheduler central** qui orchestre trois portails d'interaction distincts, tous connectés à la mémoire persistante.

---

## Composants Principaux

### 1. LIAAutonomousScheduler

**Fichier** : `simulation_service/src/simulation_service/autonomous_scheduler.py`

**Responsabilités** :
- Boucle principale asynchrone
- Gestion des intervalles temporels
- Déclenchement automatique des actions
- Gestion d'erreurs et reprise
- Monitoring et logging

**Structure** :

```python
class LIAAutonomousScheduler:
    """Scheduler qui fait tourner LIA en autonomie."""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.orchestrator = SimulationOrchestrator()
        self.local_llm = LocalLLMAdapter(...)
        self.last_research = datetime.now()
        self.last_eval = datetime.now()
        self.last_reflection = datetime.now()
        self.running = False
    
    async def start(self):
        """Démarre le scheduler."""
        self.running = True
        await self.run_autonomous_loop()
    
    async def stop(self):
        """Arrête le scheduler."""
        self.running = False
    
    async def run_autonomous_loop(self):
        """Boucle principale d'autonomie."""
        while self.running:
            try:
                # 1. Vérifier objectifs personnels (toutes les minutes)
                await self.process_personal_goals()
                
                # 2. Auto-recherche (toutes les 2h)
                if self._should_trigger_research():
                    await self.trigger_auto_research()
                
                # 3. Auto-évaluation (1x par jour)
                if self._should_trigger_evaluation():
                    await self.trigger_auto_evaluation()
                
                # 4. Auto-réflexion (toutes les 6h)
                if self._should_trigger_reflection():
                    await self.trigger_reflection()
                
                await asyncio.sleep(60)  # Vérifier toutes les minutes
                
            except Exception as e:
                logger.error(f"Erreur dans boucle autonome: {e}")
                await asyncio.sleep(60)  # Reprendre après 1 minute
```

---

### 2. Système d'Objectifs Personnels

**Extension memory_service** :

**Table SQL** :

```sql
CREATE TABLE personal_goals (
    goal_id TEXT PRIMARY KEY,
    goal_type TEXT NOT NULL,  -- 'research', 'hobby', 'task'
    description TEXT NOT NULL,
    priority REAL DEFAULT 0.5,
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'paused'
    trigger_conditions TEXT,  -- JSON
    frequency TEXT,  -- 'hourly', 'daily', 'weekly', 'custom'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP,
    next_trigger_at TIMESTAMP
);
```

**Modèle Python** :

```python
class PersonalGoal(BaseModel):
    goal_id: str
    goal_type: Literal["research", "hobby", "task"]
    description: str
    priority: float = 0.5
    status: Literal["active", "completed", "paused"] = "active"
    trigger_conditions: Optional[Dict] = None
    frequency: str
    created_at: datetime
    last_triggered_at: Optional[datetime] = None
    next_trigger_at: Optional[datetime] = None
```

**API Endpoints** :

```python
# memory_service/src/memory_service/api.py

@app.post("/personal-goals")
async def create_personal_goal(goal: PersonalGoalCreate):
    """Créer un objectif personnel."""
    ...

@app.get("/personal-goals")
async def get_personal_goals(
    status: Optional[str] = None,
    goal_type: Optional[str] = None
):
    """Lister les objectifs personnels."""
    ...

@app.put("/personal-goals/{goal_id}")
async def update_personal_goal(goal_id: str, goal: PersonalGoalUpdate):
    """Mettre à jour un objectif."""
    ...

@app.delete("/personal-goals/{goal_id}")
async def delete_personal_goal(goal_id: str):
    """Supprimer un objectif."""
    ...
```

---

### 3. Portail Autonome

**Fichier** : `simulation_service/src/simulation_service/portals/autonomous_portal.py`

**Fonctionnalités** :

#### Auto-recherche

```python
class AutonomousPortal:
    """Portail pour actions autonomes de LIA."""
    
    async def choose_research_topic(self) -> str:
        """LIA choisit un sujet à explorer basé sur sa curiosité."""
        # 1. Récupérer traits (curiosité, intérêts)
        context = await self.memory_service.get_context(session_id="autonomous")
        traits = context.get("traits", [])
        curiosity = next((t for t in traits if t["trait_id"] == "curiosity"), None)
        
        # 2. Récupérer hobbies et intérêts
        goals = await self.memory_service.get_personal_goals(goal_type="hobby")
        
        # 3. Utiliser LLM local pour choisir un sujet
        prompt = f"""
        Basé sur ma curiosité ({curiosity['value']}) et mes intérêts ({goals}),
        quel sujet devrais-je explorer maintenant ?
        Réponds avec un seul sujet spécifique.
        """
        
        topic = await self.local_llm.send_message(prompt)
        return topic.strip()
    
    async def research_topic(self, topic: str):
        """LIA explore un sujet et crée un souvenir."""
        # 1. Explorer le sujet via LLM local
        prompt = f"Explique-moi en détail : {topic}"
        insights = await self.local_llm.send_message(prompt)
        
        # 2. Journaliser dans la mémoire
        await self.memory_service.create_memory(
            category="research",
            content=f"Recherche sur {topic}: {insights}",
            importance_score=0.7,
            tags=[topic, "autonomous", "research"]
        )
        
        # 3. Mettre à jour curiosité (optionnel)
        await self._update_curiosity_from_research(topic, insights)
```

#### Auto-réflexion

```python
    async def reflect_on_interactions(self):
        """LIA analyse ses interactions récentes."""
        # 1. Récupérer interactions récentes (24h)
        recent_interactions = await self.memory_service.get_recent_interactions(
            hours=24
        )
        
        # 2. Analyser avec LLM local
        prompt = f"""
        Analyse mes interactions récentes :
        {recent_interactions}
        
        Quels insights peux-tu en tirer sur ma personnalité ?
        Qu'est-ce que j'ai appris ?
        """
        
        reflection = await self.local_llm.send_message(prompt)
        
        # 3. Créer souvenir de réflexion
        await self.memory_service.create_memory(
            category="reflection",
            content=f"Réflexion autonome: {reflection}",
            importance_score=0.8,
            tags=["autonomous", "reflection"]
        )
        
        # 4. Ajuster traits si nécessaire (garde-fous)
        await self._adjust_traits_from_reflection(reflection)
```

---

### 4. Portail Multi-Agent

**Fichier** : `simulation_service/src/simulation_service/portals/multiagent_portal.py`

**Fonctionnalités** :

#### Auto-évaluation

```python
class MultiAgentPortal:
    """Portail pour auto-évaluation multi-agent."""
    
    async def trigger_auto_evaluation(self):
        """Déclenche une simulation d'auto-évaluation."""
        # 1. Sélectionner agent partenaire
        partner_agent = await self._select_evaluation_partner()
        
        # 2. Lancer simulation
        request = SimulationStartRequest(
            agent_configs=[
                AgentConfig(agent_id="lia-primary", agent_type="lia-primary"),
                AgentConfig(agent_id=partner_agent, agent_type="llm-external")
            ],
            max_turns=10,
            scenario="personnification_test"
        )
        
        session = await self.orchestrator.start_simulation(request)
        
        # 3. Lancer quelques échanges automatiques
        for i in range(5):
            response = await self.orchestrator.process_message(
                session_id=session.session_id,
                message_content=f"Message test {i}",
                agent_id="lia-primary"
            )
        
        # 4. Calculer métrique tromperie
        deception_rate = await self.calculate_deception_rate(session)
        
        # 5. Journaliser résultats
        await self.memory_service.create_experience(
            experience_id=f"eval-{session.session_id}",
            title="Auto-évaluation personnification",
            metrics_snapshot={"deception_rate": deception_rate}
        )
        
        return session, deception_rate
```

#### Métrique "Taux de Tromperie"

```python
    async def calculate_deception_rate(self, session: SimulationSession) -> float:
        """Calcule le taux de tromperie (passer pour humain)."""
        # 1. Analyser les réponses de LIA
        lia_responses = [
            msg.content for msg in session.messages 
            if msg.agent_id == "lia-primary"
        ]
        
        # 2. Analyser les réponses du partenaire
        partner_responses = [
            msg.content for msg in session.messages 
            if msg.agent_id != "lia-primary"
        ]
        
        # 3. Utiliser LLM local pour évaluer si LIA passe pour humain
        evaluation_prompt = f"""
        Analyse ces échanges :
        LIA: {lia_responses}
        Partenaire: {partner_responses}
        
        Est-ce que LIA passe pour humain ? (oui/non)
        """
        
        evaluation = await self.local_llm.send_message(evaluation_prompt)
        
        # 4. Calculer taux (simplifié pour début)
        # En production, utiliser plusieurs évaluations
        is_human = "oui" in evaluation.lower()
        
        # 5. Mettre à jour métrique globale
        await self._update_deception_metric(is_human)
        
        return 1.0 if is_human else 0.0  # Simplifié
```

---

### 5. Portail Humain

**Fichier** : `simulation_service/src/simulation_service/portals/human_portal.py`

**Fonctionnalités** :

```python
class HumanPortal:
    """Portail pour interaction et supervision humaine."""
    
    async def get_autonomous_activity(self) -> Dict:
        """Récupère l'activité autonome récente."""
        return {
            "last_research": await self._get_last_research(),
            "last_evaluation": await self._get_last_evaluation(),
            "last_reflection": await self._get_last_reflection(),
            "active_goals": await self.memory_service.get_personal_goals(status="active"),
            "deception_rate": await self._get_deception_rate(),
            "recent_memories": await self._get_recent_memories()
        }
    
    async def pause_autonomy(self):
        """Met en pause l'autonomie."""
        await self.scheduler.stop()
    
    async def resume_autonomy(self):
        """Reprend l'autonomie."""
        await self.scheduler.start()
    
    async def interact_with_lia(self, message: str) -> str:
        """Interagit avec LIA via portail humain."""
        # Récupérer contexte
        context = await self.memory_service.get_context(session_id="human-interaction")
        
        # Générer réponse
        response = await self.local_llm.send_message(message, context=context)
        
        # Journaliser
        await self.memory_service.create_interaction(
            prompt=message,
            response=response,
            session_id="human-interaction"
        )
        
        return response
```

---

## Flux de Données

### Flux Auto-recherche

```
Scheduler (2h)
  → AutonomousPortal.choose_research_topic()
  → LocalLLM (choix sujet)
  → AutonomousPortal.research_topic()
  → LocalLLM (exploration)
  → MemoryService.create_memory()
  → Base de données
```

### Flux Auto-évaluation

```
Scheduler (24h)
  → MultiAgentPortal.trigger_auto_evaluation()
  → SimulationOrchestrator.start_simulation()
  → Échanges automatiques
  → MultiAgentPortal.calculate_deception_rate()
  → MemoryService.create_experience()
  → Base de données
```

### Flux Auto-réflexion

```
Scheduler (6h)
  → AutonomousPortal.reflect_on_interactions()
  → MemoryService.get_recent_interactions()
  → LocalLLM (analyse)
  → MemoryService.create_memory()
  → Base de données
```

---

## Gestion d'Erreurs

### Stratégie

1. **Erreurs temporaires** : Retry avec backoff exponentiel
2. **Erreurs critiques** : Log, notification, pause scheduler
3. **Erreurs LLM** : Fallback vers API externe si configuré
4. **Erreurs mémoire** : Retry, puis skip action

### Exemple

```python
async def trigger_auto_research(self):
    """Déclenche auto-recherche avec gestion d'erreurs."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            topic = await self.autonomous_portal.choose_research_topic()
            await self.autonomous_portal.research_topic(topic)
            return
        except Exception as e:
            logger.error(f"Erreur auto-recherche (tentative {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Backoff
            else:
                logger.critical("Échec auto-recherche après 3 tentatives")
                # Notification ou pause scheduler
```

---

## Performance

### Optimisations

1. **Cache modèle** : Modèle LLM chargé une fois, réutilisé
2. **Intervalles intelligents** : Pas d'actions si système occupé
3. **Chargement à la demande** : Modèle déchargé si inactif
4. **Parallélisation** : Actions indépendantes en parallèle

### Monitoring

```python
class SchedulerMetrics:
    """Métriques du scheduler."""
    
    def __init__(self):
        self.actions_executed = 0
        self.errors_count = 0
        self.avg_latency = 0.0
        self.memory_usage_mb = 0.0
    
    def record_action(self, action_type: str, latency: float):
        """Enregistre une action."""
        self.actions_executed += 1
        self.avg_latency = (self.avg_latency + latency) / 2
```

---

## Sécurité et Garde-fous

### Limites

1. **Limite actions/jour** : Max 50 actions autonomes/jour
2. **Limite ajustements traits** : Max 3 ajustements/jour
3. **Limite simulations** : Max 1 simulation/jour
4. **Limite mémoire** : Alert si > 1000 souvenirs

### Garde-fous

1. **Gouvernance** : Chaque action vérifiée par `POST /governance/check`
2. **Dérive** : Alert si dérive personnalité > seuil
3. **Boucles** : Détection et arrêt automatique

---

## Tests

### Tests Unitaires

- Tests scheduler (boucle, intervalles)
- Tests portails (recherche, réflexion, évaluation)
- Tests objectifs personnels (CRUD)

### Tests d'Intégration

- Test scheduler complet (24h)
- Test auto-recherche génère souvenirs
- Test auto-évaluation fonctionne
- Test métrique tromperie

### Tests de Performance

- Test consommation CPU/RAM
- Test latence actions
- Test impact autres services

---

## Conclusion

Cette architecture permet à LIA de fonctionner de manière autonome tout en restant contrôlable et observable via le portail humain. Les trois portails (autonome, multi-agent, humain) offrent une séparation claire des responsabilités et facilitent la maintenance.



