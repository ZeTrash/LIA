"""Portail Humain pour supervision et interaction (Étape 2.6)."""

import logging
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, Optional, List

from ..autonomous_scheduler import LIAAutonomousScheduler, SchedulerStatus

logger = logging.getLogger(__name__)


class HumanPortal:
    """Portail pour supervision et interaction humaine."""
    
    def __init__(self, scheduler: LIAAutonomousScheduler):
        """
        Initialise le portail humain.
        
        Args:
            scheduler: Scheduler autonome à superviser
        """
        self.scheduler = scheduler
        self.activity_log: List[Dict[str, Any]] = []
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Récupère le statut du scheduler.
        
        Returns:
            Statut détaillé du scheduler
        """
        status = self.scheduler.get_status()
        
        return {
            "running": status.running,
            "uptime_seconds": status.uptime_seconds,
            "actions_triggered_total": status.actions_triggered_total,
            "errors_count": status.errors_count,
            "last_research_at": status.last_research_at.isoformat() if status.last_research_at else None,
            "last_evaluation_at": status.last_evaluation_at.isoformat() if status.last_evaluation_at else None,
            "last_reflection_at": status.last_reflection_at.isoformat() if status.last_reflection_at else None,
            "last_goals_check_at": status.last_goals_check_at.isoformat() if status.last_goals_check_at else None,
            "config": {
                "enabled": self.scheduler.config.enabled,
                "goals_check_seconds": self.scheduler.config.goals_check_seconds,
                "auto_research_hours": self.scheduler.config.auto_research_hours,
                "auto_reflection_hours": self.scheduler.config.auto_reflection_hours,
                "auto_evaluation_hours": self.scheduler.config.auto_evaluation_hours,
            },
        }
    
    async def pause_scheduler(self) -> None:
        """Met le scheduler en pause."""
        if not self.scheduler.running:
            logger.warning("Scheduler déjà arrêté")
            return
        
        logger.info("⏸️ Mise en pause du scheduler")
        await self.scheduler.stop()
        self._log_activity("pause", {"timestamp": datetime.now(UTC).isoformat()})
    
    async def resume_scheduler(self) -> None:
        """Reprend le scheduler."""
        if self.scheduler.running:
            logger.warning("Scheduler déjà en cours d'exécution")
            return
        
        logger.info("▶️ Reprise du scheduler")
        # Note: Le scheduler doit être redémarré via start()
        # Cette méthode sert plutôt à réactiver la configuration
        self.scheduler.config.enabled = True
        self._log_activity("resume", {"timestamp": datetime.now(UTC).isoformat()})
    
    async def get_activity_log(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Récupère le journal d'activité.
        
        Args:
            hours: Nombre d'heures à récupérer
        
        Returns:
            Liste des activités
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        
        # Filtrer les activités récentes
        recent_activities = [
            activity for activity in self.activity_log
            if datetime.fromisoformat(activity["timestamp"].replace("Z", "+00:00")) >= cutoff
        ]
        
        return recent_activities
    
    def _log_activity(self, action: str, metadata: Dict[str, Any]) -> None:
        """Enregistre une activité dans le journal."""
        activity = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "metadata": metadata,
        }
        self.activity_log.append(activity)
        
        # Limiter la taille du journal (garder les 1000 dernières entrées)
        if len(self.activity_log) > 1000:
            self.activity_log = self.activity_log[-1000:]
    
    async def adjust_intervals(
        self,
        goals_check_seconds: Optional[int] = None,
        auto_research_hours: Optional[int] = None,
        auto_reflection_hours: Optional[int] = None,
        auto_evaluation_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Ajuste les intervalles du scheduler.
        
        Args:
            goals_check_seconds: Nouvel intervalle pour vérification objectifs
            auto_research_hours: Nouvel intervalle pour auto-recherche
            auto_reflection_hours: Nouvel intervalle pour auto-réflexion
            auto_evaluation_hours: Nouvel intervalle pour auto-évaluation
        
        Returns:
            Configuration mise à jour
        """
        if goals_check_seconds is not None:
            self.scheduler.config.goals_check_seconds = goals_check_seconds
        if auto_research_hours is not None:
            self.scheduler.config.auto_research_hours = auto_research_hours
        if auto_reflection_hours is not None:
            self.scheduler.config.auto_reflection_hours = auto_reflection_hours
        if auto_evaluation_hours is not None:
            self.scheduler.config.auto_evaluation_hours = auto_evaluation_hours
        
        self._log_activity("adjust_intervals", {
            "goals_check_seconds": goals_check_seconds,
            "auto_research_hours": auto_research_hours,
            "auto_reflection_hours": auto_reflection_hours,
            "auto_evaluation_hours": auto_evaluation_hours,
        })
        
        logger.info(f"⚙️ Intervalles ajustés")
        
        return await self.get_scheduler_status()
