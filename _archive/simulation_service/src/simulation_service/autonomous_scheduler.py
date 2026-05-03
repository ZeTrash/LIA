"""Scheduler autonome pour LIA (Étape 2.6)."""

import asyncio
import logging
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, Optional

import httpx

from .config import get_settings
from .orchestrator import SimulationOrchestrator
from .adapters import LocalLLMAdapter, AgentConfig

logger = logging.getLogger(__name__)


class AutonomousConfig:
    """Configuration du scheduler autonome."""
    
    def __init__(
        self,
        enabled: bool = True,
        goals_check_seconds: int = 60,
        auto_research_hours: int = 2,
        auto_reflection_hours: int = 6,
        auto_evaluation_hours: int = 24,
        max_retries: int = 3,
        retry_delay_seconds: int = 300,
        auto_restart: bool = True,
    ):
        self.enabled = enabled
        self.goals_check_seconds = goals_check_seconds
        self.auto_research_hours = auto_research_hours
        self.auto_reflection_hours = auto_reflection_hours
        self.auto_evaluation_hours = auto_evaluation_hours
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.auto_restart = auto_restart


class SchedulerStatus:
    """Statut du scheduler."""
    
    def __init__(self):
        self.running: bool = False
        self.uptime_seconds: float = 0.0
        self.actions_triggered_total: int = 0
        self.errors_count: int = 0
        self.last_research_at: Optional[datetime] = None
        self.last_evaluation_at: Optional[datetime] = None
        self.last_reflection_at: Optional[datetime] = None
        self.last_goals_check_at: Optional[datetime] = None


class LIAAutonomousScheduler:
    """Scheduler qui fait tourner LIA en autonomie."""
    
    def __init__(
        self,
        memory_service_url: str,
        orchestrator: SimulationOrchestrator,
        local_llm_config: Optional[AgentConfig] = None,
        config: Optional[AutonomousConfig] = None,
    ):
        """
        Initialise le scheduler autonome.
        
        Args:
            memory_service_url: URL du service mémoire
            orchestrator: Orchestrateur simulation (Étape 2)
            local_llm_config: Configuration pour LocalLLMAdapter (optionnel)
            config: Configuration du scheduler (optionnel)
        """
        self.memory_service_url = memory_service_url
        self.orchestrator = orchestrator
        self.config = config or AutonomousConfig()
        self.settings = get_settings()
        
        # Client HTTP pour memory_service
        self.memory_client = httpx.AsyncClient(
            base_url=memory_service_url,
            timeout=30.0
        )
        
        # LocalLLMAdapter (optionnel, chargé à la demande)
        self.local_llm: Optional[LocalLLMAdapter] = None
        if local_llm_config:
            self.local_llm = LocalLLMAdapter(local_llm_config)
        elif self.settings.local_llm_model:
            # Créer config par défaut
            default_config = AgentConfig(
                agent_id="lia-autonomous",
                agent_type="llm-local"
            )
            self.local_llm = LocalLLMAdapter(default_config)
        
        # État du scheduler
        self.running = False
        self.status = SchedulerStatus()
        self.start_time: Optional[datetime] = None
        
        # Timestamps des dernières actions
        self.last_goals_check = datetime.now(UTC)
        self.last_research = datetime.now(UTC)
        self.last_reflection = datetime.now(UTC)
        self.last_evaluation = datetime.now(UTC)
        
        # Compteurs d'erreurs
        self.consecutive_errors = 0
        self.restart_count = 0
        self.max_restarts_per_day = 3
        
        # Initialiser les portails
        from .portals import AutonomousPortal, MultiAgentPortal
        
        self.autonomous_portal = AutonomousPortal(
            memory_service_url=memory_service_url,
            local_llm=self.local_llm,
        )
        self.multi_agent_portal = MultiAgentPortal(
            orchestrator=orchestrator,
            memory_service_url=memory_service_url,
        )
    
    async def start(self) -> None:
        """Démarre le scheduler (boucle principale)."""
        if not self.config.enabled:
            logger.info("Scheduler autonome désactivé")
            return
        
        if self.running:
            logger.warning("Scheduler déjà en cours d'exécution")
            return
        
        self.running = True
        self.start_time = datetime.now(UTC)
        self.status.running = True
        logger.info("🚀 Démarrage du scheduler autonome LIA")
        
        try:
            await self.run_autonomous_loop()
        except Exception as e:
            logger.error(f"❌ Erreur critique dans le scheduler: {e}", exc_info=True)
            self.status.errors_count += 1
            raise
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Arrête le scheduler proprement."""
        if not self.running:
            return
        
        logger.info("🛑 Arrêt du scheduler autonome")
        self.running = False
        self.status.running = False
        
        # Fermer le client HTTP
        await self.memory_client.aclose()
        
        # Fermer les portails
        if self.autonomous_portal:
            await self.autonomous_portal.close()
        
        # Décharger le modèle LLM si chargé
        if self.local_llm:
            try:
                self.local_llm.unload_model()
            except Exception:
                pass
    
    async def run_autonomous_loop(self) -> None:
        """Boucle principale d'autonomie."""
        while self.running:
            try:
                now = datetime.now(UTC)
                
                # Mettre à jour l'uptime
                if self.start_time:
                    self.status.uptime_seconds = (now - self.start_time).total_seconds()
                
                # Vérifier objectifs personnels (toutes les 60s par défaut)
                if (now - self.last_goals_check).total_seconds() >= self.config.goals_check_seconds:
                    await self._safe_execute(self.check_personal_goals, "check_personal_goals")
                    self.last_goals_check = now
                    self.status.last_goals_check_at = now
                
                # Auto-recherche (toutes les 2h par défaut)
                research_interval = self.config.auto_research_hours * 3600
                if (now - self.last_research).total_seconds() >= research_interval:
                    await self._safe_execute(self.trigger_auto_research, "trigger_auto_research")
                    self.last_research = now
                    self.status.last_research_at = now
                
                # Auto-réflexion (toutes les 6h par défaut)
                reflection_interval = self.config.auto_reflection_hours * 3600
                if (now - self.last_reflection).total_seconds() >= reflection_interval:
                    await self._safe_execute(self.trigger_auto_reflection, "trigger_auto_reflection")
                    self.last_reflection = now
                    self.status.last_reflection_at = now
                
                # Auto-évaluation (toutes les 24h par défaut)
                evaluation_interval = self.config.auto_evaluation_hours * 3600
                if (now - self.last_evaluation).total_seconds() >= evaluation_interval:
                    await self._safe_execute(self.trigger_auto_evaluation, "trigger_auto_evaluation")
                    self.last_evaluation = now
                    self.status.last_evaluation_at = now
                
                # Réinitialiser compteur d'erreurs si succès
                self.consecutive_errors = 0
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}", exc_info=True)
                self.consecutive_errors += 1
                self.status.errors_count += 1
                
                # Si trop d'erreurs consécutives, arrêter
                if self.consecutive_errors >= self.config.max_retries:
                    logger.error(f"Trop d'erreurs consécutives ({self.consecutive_errors}), arrêt du scheduler")
                    break
                
                # Attendre avant retry
                await asyncio.sleep(self.config.retry_delay_seconds)
            
            # Pause entre itérations
            await asyncio.sleep(10)  # Vérifier toutes les 10 secondes
    
    async def _safe_execute(self, coro_func, action_name: str) -> None:
        """Exécute une action de manière sécurisée avec gestion d'erreurs."""
        try:
            await coro_func()
            self.status.actions_triggered_total += 1
            logger.info(f"✅ Action déclenchée: {action_name}")
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Timeout pour {action_name}")
            self.status.errors_count += 1
        except Exception as e:
            logger.error(f"❌ Erreur lors de {action_name}: {e}", exc_info=True)
            self.status.errors_count += 1
    
    async def check_personal_goals(self) -> None:
        """Vérifie et déclenche les objectifs personnels (intervalle: 60s)."""
        try:
            # Récupérer les objectifs à déclencher depuis memory_service
            response = await self.memory_client.get("/personal-goals", params={"status": "active"})
            response.raise_for_status()
            all_goals = response.json()
            
            # Filtrer ceux qui doivent être déclenchés (next_trigger_at <= now)
            now = datetime.now(UTC)
            goals_to_trigger = [
                goal for goal in all_goals
                if goal.get("next_trigger_at") and
                datetime.fromisoformat(goal["next_trigger_at"].replace("Z", "+00:00")) <= now
            ]
            
            if not goals_to_trigger:
                return
            
            logger.info(f"📋 {len(goals_to_trigger)} objectif(s) à déclencher")
            
            # Déclencher chaque objectif
            for goal in goals_to_trigger:
                goal_type = goal.get("goal_type")
                goal_id = goal.get("goal_id")
                
                try:
                    if goal_type == "research":
                        # Déclencher auto-recherche
                        await self.trigger_auto_research(goal.get("description"))
                    elif goal_type == "hobby":
                        # Traiter comme hobby (peut être implémenté plus tard)
                        logger.info(f"🎨 Hobby déclenché: {goal.get('description')}")
                    elif goal_type == "task":
                        # Tâche spécifique (peut être implémenté plus tard)
                        logger.info(f"📝 Tâche déclenchée: {goal.get('description')}")
                    
                    # Mettre à jour last_triggered_at et next_trigger_at
                    await self._update_goal_trigger_time(goal_id, goal.get("frequency"))
                    
                except Exception as e:
                    logger.error(f"Erreur lors du déclenchement de l'objectif {goal_id}: {e}")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP lors de la vérification des objectifs: {e.response.text}")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des objectifs: {e}", exc_info=True)
    
    async def _update_goal_trigger_time(self, goal_id: str, frequency: str) -> None:
        """Met à jour les timestamps d'un objectif après déclenchement."""
        try:
            now = datetime.now(UTC)
            next_trigger = None
            
            if frequency == "daily":
                next_trigger = now + timedelta(days=1)
            elif frequency == "weekly":
                next_trigger = now + timedelta(weeks=1)
            elif frequency == "monthly":
                next_trigger = now + timedelta(days=30)
            # Pour "once", next_trigger reste None
            
            update_data = {
                "last_triggered_at": now.isoformat(),
                "next_trigger_at": next_trigger.isoformat() if next_trigger else None,
            }
            
            response = await self.memory_client.put(f"/personal-goals/{goal_id}", json=update_data)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'objectif {goal_id}: {e}")
    
    async def trigger_auto_research(self, topic: Optional[str] = None) -> None:
        """Déclenche une auto-recherche (intervalle: 2h)."""
        logger.info("🔍 Déclenchement auto-recherche")
        
        # Utiliser le portail autonome
        if self.autonomous_portal:
            if not topic:
                context = await self.autonomous_portal._get_memory_context()
                topic = await self.autonomous_portal.choose_research_topic(context)
            
            await self.autonomous_portal.research_topic(topic)
        else:
            logger.warning("Portail autonome non initialisé")
    
    async def trigger_auto_evaluation(self) -> None:
        """Déclenche une auto-évaluation (intervalle: 24h)."""
        logger.info("📊 Déclenchement auto-évaluation")
        
        # Utiliser le portail multi-agent
        if self.multi_agent_portal:
            await self.multi_agent_portal.trigger_auto_evaluation()
        else:
            logger.warning("Portail multi-agent non initialisé")
    
    async def trigger_auto_reflection(self) -> None:
        """Déclenche une auto-réflexion (intervalle: 6h)."""
        logger.info("🤔 Déclenchement auto-réflexion")
        
        # Utiliser le portail autonome
        if self.autonomous_portal:
            await self.autonomous_portal.reflect_on_interactions(window_hours=24)
        else:
            logger.warning("Portail autonome non initialisé")
    
    def get_status(self) -> SchedulerStatus:
        """Retourne le statut actuel du scheduler."""
        return self.status
