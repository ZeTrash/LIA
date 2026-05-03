# Révision de l'Architecture - Vision Autonome de LIA

## Vision Révisée : LIA comme Agent Autonome

### Inspiration : Android (Dark Matter)
LIA doit être un agent **autonome** qui :
- Fonctionne de lui-même, sans intervention humaine constante
- Développe sa personnalité par auto-apprentissage
- A sa propre "porte" d'accès (interface autonome)
- Peut interagir avec d'autres agents pour s'auto-évaluer
- Objectif : "tromper" d'autres agents (test de personnification)

### Problèmes de l'Architecture Actuelle

1. **Trop manuelle** : Nécessite des commandes CLI pour chaque action
2. **Pas d'autonomie** : LIA ne fonctionne pas "en arrière-plan"
3. **Dépendance API externe** : Gemini/OpenAI = coûts, latence, limites
4. **Pas de boucle autonome** : Pas de système qui fait tourner LIA en continu

---

## Architecture Révisée : LIA Autonome

### 1. Moteur LLM Local (au lieu d'API externe)

#### Options de Modèles Locaux "Vierges"

| Modèle | Taille | Avantages | Inconvénients | Recommandation |
|--------|--------|-----------|---------------|----------------|
| **Llama 3.2** (Meta) | 1B, 3B | Très léger, open-source, modulaire | Qualité limitée | ✅ **Recommandé pour début** |
| **Mistral 7B** | 7B | Bon équilibre qualité/taille | Nécessite GPU | ✅ **Recommandé si GPU disponible** |
| **Phi-3** (Microsoft) | 3.8B | Optimisé, performant | Plus petit vocabulaire | ✅ Alternative |
| **Qwen2.5** (Alibaba) | 0.5B-7B | Très modulaire, multilingue | Moins connu | ⚠️ À tester |
| **TinyLlama** | 1.1B | Ultra-léger | Qualité très limitée | ❌ Trop limité |

#### Pourquoi un Modèle Local ?

1. **Contrôle total** : Pas de filtres, pas de limites de rate
2. **Coûts** : Gratuit après installation
3. **Privacy** : Données restent locales
4. **Modularité** : On peut fine-tuner sur la personnalité de LIA
5. **Autonomie** : Fonctionne sans connexion internet

#### Architecture Technique

```
┌─────────────────────────────────────────────────┐
│         LIA Core (Service Autonome)             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │  LLM Local   │◄────►│  Memory      │        │
│  │  (Llama/Mist)│      │  Service    │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│         │                     ▼                 │
│         │              ┌──────────────┐         │
│         │              │  Base de     │         │
│         │              │  Données     │         │
│         │              │  (Personnalité)│       │
│         │              └──────────────┘         │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐                              │
│  │  Boucle      │                              │
│  │  Autonome    │                              │
│  │  (Scheduler) │                              │
│  └──────┬───────┘                              │
│         │                                       │
│         ▼                                       │
│  ┌──────────────────────────────────────┐     │
│  │  Portails d'Interaction              │     │
│  ├──────────────────────────────────────┤     │
│  │  • Portail Autonome (auto-recherche) │     │
│  │  • Portail Multi-Agent (auto-éval)    │     │
│  │  • Portail Humain (supervision)      │     │
│  └──────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

### 2. Boucle Autonome (Scheduler)

LIA doit avoir un **scheduler** qui :
- Tourne en arrière-plan (daemon/service)
- Déclenche des actions automatiques :
  - **Auto-recherche** : LIA explore des sujets de ses hobbies
  - **Auto-évaluation** : LIA lance des simulations multi-agent
  - **Auto-réflexion** : LIA analyse ses interactions passées
  - **Tâches personnelles** : LIA gère ses propres objectifs

#### Exemple de Boucle

```python
# Pseudo-code du scheduler
while True:
    # 1. Vérifier les objectifs personnels
    goals = memory_service.get_personal_goals()
    for goal in goals:
        if goal.should_trigger():
            lia.execute_goal(goal)  # Ex: "Explorer la philosophie"
    
    # 2. Auto-recherche (toutes les 2h)
    if time_since_last_research > 2h:
        topic = lia.choose_research_topic()  # Basé sur curiosité
        lia.research(topic)
        lia.update_memory(topic, insights)
    
    # 3. Auto-évaluation (1x par jour)
    if time_since_last_eval > 24h:
        lia.launch_self_evaluation_simulation()
    
    # 4. Réflexion (toutes les 6h)
    if time_since_last_reflection > 6h:
        lia.reflect_on_recent_interactions()
    
    sleep(60)  # Vérifier toutes les minutes
```

### 3. Portails d'Interaction

#### Portail 1 : Autonome (LIA seule)
- LIA explore, apprend, réfléchit
- Pas d'intervention humaine
- Journalisé dans la mémoire

#### Portail 2 : Multi-Agent (Auto-évaluation)
- LIA lance automatiquement des simulations
- Teste sa personnalité contre d'autres agents
- Objectif : "tromper" l'autre agent (passer pour humain)

#### Portail 3 : Humain (Supervision)
- Interface pour interagir avec LIA
- Supervision et ajustements
- Lecture des journaux d'activité

### 4. Système de Personnalité Auto-Évolutive

LIA doit pouvoir :
- **Décider** quels sujets explorer (basé sur curiosité)
- **Créer** ses propres objectifs personnels
- **Ajuster** ses traits après auto-évaluation
- **Apprendre** de ses interactions sans supervision

---

## Plan de Migration

### Phase 1 : Intégration Modèle Local (Priorité 1)

1. **Choisir le modèle** : Recommandation = **Llama 3.2 3B** (ou Mistral 7B si GPU)
2. **Intégrer avec Ollama** ou **llama.cpp** :
   - Ollama : Plus simple, gestion automatique
   - llama.cpp : Plus de contrôle, meilleure performance
3. **Créer un adapter local** : Remplacer `ExternalLLMAdapter` par `LocalLLMAdapter`
4. **Tester** : Vérifier que LIA peut générer des réponses avec le modèle local

### Phase 2 : Boucle Autonome (Priorité 2)

1. **Créer le scheduler** : Service qui tourne en arrière-plan
2. **Implémenter les déclencheurs** :
   - Auto-recherche
   - Auto-évaluation
   - Auto-réflexion
3. **Gérer les objectifs personnels** : Système de goals dans la mémoire

### Phase 3 : Portails (Priorité 3)

1. **Portail autonome** : Interface pour voir ce que LIA fait seule
2. **Portail multi-agent amélioré** : Simulations automatiques
3. **Portail humain** : Interface de supervision

---

## Recommandations Techniques

### Modèle LLM Local

**Option A : Ollama (Recommandé pour début)**
```bash
# Installation simple
ollama pull llama3.2:3b

# Utilisation
ollama run llama3.2:3b "Bonjour, je suis LIA"
```

**Avantages** :
- Installation en 1 commande
- Gestion automatique du modèle
- API REST simple

**Option B : llama.cpp (Plus de contrôle)**
- Meilleure performance
- Plus de contrôle sur l'inférence
- Nécessite compilation

### Intégration dans le Code

Créer `LocalLLMAdapter` :

```python
class LocalLLMAdapter(AgentAdapter):
    """Adapter pour LLM local (Ollama/llama.cpp)."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.model_name = config.model_name or "llama3.2:3b"
        self.ollama_url = config.ollama_url or "http://localhost:11434"
    
    async def send_message(self, message: str, context: Optional[Dict] = None, session_id: Optional[str] = None) -> str:
        # Construire le prompt avec contexte
        prompt = self.build_prompt(message, context)
        
        # Appel Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()["response"]
```

### Scheduler Autonome

Créer `lia_autonomous_service.py` :

```python
import asyncio
from datetime import datetime, timedelta
from simulation_service.orchestrator import SimulationOrchestrator
from memory_service import MemoryService

class LIAAutonomousService:
    """Service qui fait tourner LIA en autonomie."""
    
    def __init__(self):
        self.orchestrator = SimulationOrchestrator()
        self.memory = MemoryService()
        self.last_research = datetime.now()
        self.last_eval = datetime.now()
        self.last_reflection = datetime.now()
    
    async def run_autonomous_loop(self):
        """Boucle principale d'autonomie."""
        while True:
            await self.check_personal_goals()
            await self.check_auto_research()
            await self.check_auto_evaluation()
            await self.check_reflection()
            await asyncio.sleep(60)  # Vérifier toutes les minutes
    
    async def check_auto_research(self):
        """Déclenche une recherche automatique."""
        if datetime.now() - self.last_research > timedelta(hours=2):
            topic = await self.choose_research_topic()
            await self.research_topic(topic)
            self.last_research = datetime.now()
    
    async def choose_research_topic(self) -> str:
        """LIA choisit un sujet à explorer."""
        # Basé sur curiosité, hobbies, objectifs personnels
        traits = await self.memory.get_traits()
        curiosity = next((t for t in traits if t["trait_id"] == "curiosity"), None)
        # Logique de choix...
        return "philosophie"
    
    async def research_topic(self, topic: str):
        """LIA fait une recherche sur un sujet."""
        # Utiliser le LLM local pour explorer
        prompt = f"Explique-moi en détail : {topic}"
        response = await self.local_llm.generate(prompt)
        # Journaliser dans la mémoire
        await self.memory.create_memory(
            category="research",
            content=f"Recherche sur {topic}: {response}",
            importance_score=0.7
        )
```

---

## Questions à Décider

1. **Quel modèle choisir ?**
   - Llama 3.2 3B (léger, début) ✅ Recommandé
   - Mistral 7B (meilleure qualité, nécessite GPU)
   - Autre ?

2. **Ollama ou llama.cpp ?**
   - Ollama (simplicité) ✅ Recommandé pour début
   - llama.cpp (performance)

3. **Fréquence de la boucle autonome ?**
   - Auto-recherche : toutes les 2h ?
   - Auto-évaluation : 1x par jour ?
   - Auto-réflexion : toutes les 6h ?

4. **Garder l'API externe comme fallback ?**
   - Oui : Si le modèle local échoue
   - Non : 100% local

---

## Prochaines Étapes

1. ✅ **Valider cette vision** avec toi
2. **Installer Ollama + Llama 3.2 3B**
3. **Créer LocalLLMAdapter**
4. **Tester** : LIA répond avec le modèle local
5. **Créer le scheduler autonome**
6. **Implémenter les portails**

---

## Conclusion

L'architecture actuelle est **trop manuelle** pour ta vision. Il faut :
- ✅ Modèle local (au lieu d'API externe)
- ✅ Boucle autonome (scheduler)
- ✅ Portails séparés (autonome, multi-agent, humain)
- ✅ Auto-évolution de la personnalité

**Recommandation** : Commencer par intégrer Ollama + Llama 3.2 3B, puis créer le scheduler autonome.

