# Concepts Récupérés de l'Ancien Projet

**Date** : 2024-12-19  
**Source** : Archive `_archive/`  
**Objectif** : Extraire les concepts essentiels pour la nouvelle architecture

---

## Vue d'Ensemble

Ce document liste les concepts, patterns et structures récupérés de l'ancien projet qui peuvent être réutilisés dans la nouvelle architecture.

---

## 1. Mémoire Persistante

### Structure de Données

**Source** : `_archive/memory_service/src/memory_service/models.py`

#### Modèles Principaux

1. **TraitModel** (Traits de personnalité)
   - `trait_id`, `type` (persona, skill, style, constraint)
   - `label`, `value`, `version`
   - `weight`, `confidence`
   - `status` (active, staged, deprecated)
   - Versioning avec `TraitVersionModel`

2. **SouvenirModel** (Souvenirs/Mémoires)
   - `memory_id`, `category` (fact, preference, alert)
   - `content`, `tags`
   - Scores : `importance_score`, `recency_score`, `emotion_score`
   - `frequency`, `ttl` (time to live)
   - Liens avec `SouvenirLinkModel`

3. **InteractionModel** (Logs d'interactions)
   - `interaction_id`, `session_id`
   - `prompt`, `response`
   - `scores`, `derived_traits`, `anomalies`
   - `severity` (info, warning, error)

4. **SessionGoalModel** (Objectifs de session)
   - `goal_id`, `session_id`
   - `description`, `status`
   - `priority`, `deadline`

5. **ExperienceModel** (Agrégations d'interactions)
   - `experience_id`, `title`
   - `session_id`, `started_at`
   - `metrics_snapshot` (JSON)

6. **PersonalGoalModel** (Objectifs personnels - Étape 2.6)
   - `goal_id`, `goal_type` (research, hobby, task)
   - `description`, `priority`, `status`
   - `frequency` (once, daily, weekly, monthly)
   - `trigger_conditions`, `next_trigger_at`

### API REST

**Endpoints clés** :
- `GET /context` : Récupération du contexte mémoire
- `POST /interaction` : Journalisation d'une interaction
- `POST /trait-update` : Mise à jour d'un trait
- `POST /governance/check` : Vérification des garde-fous
- `GET /metrics` : Métriques d'observabilité
- `POST /personal-goals` : Création d'objectif personnel
- `GET /personal-goals` : Liste des objectifs

### Système de Gouvernance

- Scoring des souvenirs (importance, récence, émotion)
- Contrôle de dérive (ton, cohérence)
- Gestion TTL (durée de vie)
- Versioning optimiste des traits
- Purge et archivage automatiques

---

## 2. Architecture Modulaire

### Système d'Adapters

**Source** : `_archive/simulation_service/src/simulation_service/adapters.py`

#### LocalLLMAdapter (Qwen2.5-1.5B-Instruct 4 bits)

**Fonctionnalités clés** :
- Chargement Qwen2.5-1.5B-Instruct 4 bits avec quantisation (INT4/INT8)
- Cache global du modèle
- Détection automatique GPU/CPU
- Construction de prompts avec contexte mémoire
- Fallback vers API externe si erreur

**Méthodes principales** :
- `_load_model()` : Chargement avec quantisation
- `build_prompt()` : Construction prompt avec contexte
- `send_message()` : Génération de réponse
- `_clean_response()` : Nettoyage de la réponse

#### Pattern Adapter

```python
class AgentAdapter(ABC):
    """Interface de base pour adapters."""
    
    async def send_message(
        self,
        message: str,
        context: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Envoie un message et génère une réponse."""
        pass
```

### Orchestration Multi-Agent

**Source** : `_archive/simulation_service/src/simulation_service/orchestrator.py`

- Gestion de sessions multi-agent
- Rotation des tours
- Journalisation des interactions
- Métriques comportementales

---

## 3. Autonomie

### Scheduler Autonome

**Source** : `_archive/simulation_service/src/simulation_service/autonomous_scheduler.py`

#### LIAAutonomousScheduler

**Fonctionnalités** :
- Boucle principale asynchrone
- Gestion des intervalles :
  - Objectifs personnels : 60s
  - Auto-recherche : 2h (configurable)
  - Auto-réflexion : 6h (configurable)
  - Auto-évaluation : 24h (configurable)
- Gestion d'erreurs et reprise
- Monitoring et statut

**Structure** :
```python
class LIAAutonomousScheduler:
    async def run_autonomous_loop(self):
        while self.running:
            await self.check_personal_goals()
            await self.check_auto_research()
            await self.check_auto_evaluation()
            await self.check_reflection()
            await asyncio.sleep(60)
```

### Objectifs Personnels

**Source** : `_archive/charge_timeline/etape2_6_autonomie_boucle_autonome/livrables/specification_objectifs_personnels.md`

**Types** :
- `research` : Sujet à explorer
- `hobby` : Activité récurrente
- `task` : Tâche à accomplir

**Fréquences** :
- `once` : Une seule fois
- `daily` : Quotidien
- `weekly` : Hebdomadaire
- `monthly` : Mensuel

**Structure** :
```python
class PersonalGoal:
    goal_id: str
    goal_type: Literal["research", "hobby", "task"]
    description: str
    priority: float  # 0.0 - 1.0
    status: Literal["active", "paused", "completed", "archived"]
    frequency: Literal["once", "daily", "weekly", "monthly"]
    trigger_conditions: Dict[str, Any]
    next_trigger_at: datetime
```

### Portails d'Interaction

**Source** : `_archive/simulation_service/src/simulation_service/portals/`

#### AutonomousPortal

- `choose_research_topic()` : Choix sujet basé sur curiosité
- `research_topic(topic)` : Exploration via LLM local
- `reflect_on_interactions()` : Analyse interactions passées

#### MultiAgentPortal

- `trigger_auto_evaluation()` : Déclenche simulation
- `calculate_deception_rate()` : Métrique "taux de tromperie"
- `adjust_traits_from_results()` : Ajustement basé résultats

---

## 4. Modèle Local (Qwen2.5-1.5B-Instruct 4 bits)

### LocalLLMAdapter

**Source** : `_archive/simulation_service/src/simulation_service/adapters.py`

**Fonctionnalités** :
- Chargement Qwen2.5-1.5B-Instruct 4 bits (1.5B paramètres)
- Quantisation INT4/INT8 avec bitsandbytes
- Cache global pour éviter rechargement
- Détection GPU/CPU automatique
- Limitation prompt (512 tokens max pour Qwen2.5-1.5B-Instruct 4 bits)
- Construction prompt avec contexte mémoire

**Intégration Mémoire** :
- Récupération contexte via `GET /context`
- Formatage traits, souvenirs, objectifs en prompt
- Journalisation interactions après génération

**Configuration** :
- `local_llm_model` : Nom du modèle (ex: "Qwen2.5-1.5B-Instruct 4 bits")
- `local_llm_max_tokens` : Longueur max réponse
- `local_llm_temperature` : Température génération
- `local_llm_quantize` : Activer quantisation
- `local_llm_quantization_bits` : 4 ou 8 bits

---

## 5. Patterns et Bonnes Pratiques

### Configuration

- Fichiers sensibles dans `config/` (non versionnés)
- Templates `.example` pour documentation
- Variables d'environnement via `.env`

### Base de Données

- SQLite par défaut (développement)
- PostgreSQL pour production
- Migrations versionnées
- Modèles SQLAlchemy avec type hints

### Tests

- Tests unitaires pour chaque composant
- Tests d'intégration pour interactions
- Mock server pour tests isolés
- Validation avec rapports détaillés

### Logging et Observabilité

- Logging structuré
- Métriques Prometheus (optionnel)
- Tableaux de bord CLI
- Suivi des erreurs et performances

---

## 6. Concepts à Réutiliser dans la Nouvelle Architecture

### ✅ À Réutiliser Directement

1. **Structure de données mémoire** :
   - Modèles (Traits, Souvenirs, Interactions)
   - Relations et liens
   - Système de scoring

2. **Pattern Adapter** :
   - Interface abstraite
   - Implémentations concrètes
   - Gestion de contexte

3. **Système de gouvernance** :
   - Scoring et filtrage
   - Contrôle de dérive
   - Versioning

4. **Objectifs personnels** :
   - Structure de données
   - Types et fréquences
   - Conditions de déclenchement

### ⚠️ À Adapter

1. **Scheduler autonome** :
   - Adapter pour nouvelle architecture
   - Intégrer avec noyau d'appui (Gemini)
   - Simplifier si nécessaire

2. **Portails** :
   - Adapter pour nouveaux canaux
   - Intégrer canal noyau d'appui
   - Simplifier structure

3. **LocalLLMAdapter** :
   - Adapter pour nouvelle structure
   - Intégrer avec noyau d'appui
   - Simplifier configuration

### ❌ À Revoir Complètement

1. **Architecture globale** :
   - Nouvelle structure modulaire
   - Séparation claire noyau primaire / noyau d'appui
   - Nouveaux canaux d'interaction

2. **Intégration Gemini** :
   - Nouveau système pour noyau d'appui
   - Canal d'échange dédié
   - Utilisation comme source de connaissance

---

## 7. Notes Importantes

### Différences avec Nouvelle Architecture

1. **Noyau d'appui** :
   - Ancien : Gemini comme fallback optionnel
   - Nouveau : Gemini comme première source de connaissance (comme un livre)

2. **Contrôle des paramètres** :
   - Ancien : Ajustement traits seulement
   - Nouveau : Contrôle complet de tous les paramètres

3. **Structure** :
   - Ancien : Services séparés (memory_service, simulation_service)
   - Nouveau : Structure modulaire (core, memory, support, interfaces, autonomy)

### Références

- **Archive complète** : `_archive/`
- **Documentation ancienne** : `_archive/docs/`
- **Code source** : `_archive/memory_service/`, `_archive/simulation_service/`
- **Cahiers des charges** : `_archive/charge_timeline/`

---

**Date de création** : 2024-12-19  
**Statut** : Concepts extraits, prêts à être réutilisés dans nouvelle architecture

