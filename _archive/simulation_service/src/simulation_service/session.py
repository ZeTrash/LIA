"""Gestion des sessions de simulation."""

from datetime import datetime, UTC
from typing import Dict, List, Optional
from enum import Enum

from .schemas import (
    MultiAgentMessage,
    AgentConfig,
    SessionStatus,
    BehavioralMetrics
)
from .protocol import generate_session_id


class SimulationSession:
    """Représente une session de simulation."""
    
    def __init__(
        self,
        session_id: str,
        agent_configs: List[AgentConfig],
        max_turns: int = 50,
        scenario: Optional[str] = None
    ):
        self.session_id = session_id
        self.agent_configs = agent_configs
        self.agent_ids = [cfg.agent_id for cfg in agent_configs]
        self.max_turns = max_turns
        self.scenario = scenario
        
        self.status: SessionStatus = "starting"
        self.current_turn = 0
        self.messages: List[MultiAgentMessage] = []
        self.started_at = datetime.now(UTC)
        self.last_activity: Optional[datetime] = None
        self.metrics: Optional[BehavioralMetrics] = None
        self.metrics_by_agent: Dict[str, BehavioralMetrics] = {}
        self.experience_id: Optional[str] = None
        self.initial_traits: Dict[str, Dict] = {}  # Pour calculer trait_drift
        
        # Gestion des erreurs
        self.timeout_count = 0
        self.error_count = 0
        self.loop_detected = False
    
    def add_message(self, message: MultiAgentMessage) -> None:
        """Ajoute un message à la session."""
        self.messages.append(message)
        self.current_turn = max(self.current_turn, message.metadata.get("turn", 0))
        self.last_activity = datetime.now(UTC)
    
    def get_messages_by_agent(self, agent_id: str) -> List[MultiAgentMessage]:
        """Récupère tous les messages d'un agent."""
        return [msg for msg in self.messages if msg.agent_id == agent_id]
    
    def get_last_message(self) -> Optional[MultiAgentMessage]:
        """Récupère le dernier message."""
        return self.messages[-1] if self.messages else None
    
    def is_complete(self) -> bool:
        """Vérifie si la simulation est terminée."""
        return (
            self.status in ["stopped", "failed", "completed"]
            or self.current_turn >= self.max_turns
        )
    
    def get_next_agent_id(self) -> Optional[str]:
        """Retourne l'ID du prochain agent à parler (rotation)."""
        if not self.messages:
            return self.agent_ids[0] if self.agent_ids else None
        
        last_message = self.messages[-1]
        last_agent_index = self.agent_ids.index(last_message.agent_id) if last_message.agent_id in self.agent_ids else -1
        next_index = (last_agent_index + 1) % len(self.agent_ids)
        return self.agent_ids[next_index]
    
    def get_partner_agent_id(self, agent_id: str) -> Optional[str]:
        """Retourne l'ID de l'agent partenaire."""
        if agent_id not in self.agent_ids:
            return None
        
        agent_index = self.agent_ids.index(agent_id)
        partner_index = (agent_index + 1) % len(self.agent_ids)
        return self.agent_ids[partner_index]


class SessionManager:
    """Gestionnaire des sessions de simulation."""
    
    def __init__(self, max_concurrent_sessions: int = 10):
        self.sessions: Dict[str, SimulationSession] = {}
        self.max_concurrent_sessions = max_concurrent_sessions
    
    def create_session(
        self,
        agent_configs: List[AgentConfig],
        max_turns: int = 50,
        scenario: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> SimulationSession:
        """Crée une nouvelle session de simulation."""
        if len(self.sessions) >= self.max_concurrent_sessions:
            raise Exception(f"Nombre maximum de sessions ({self.max_concurrent_sessions}) atteint")
        
        if session_id is None:
            session_id = generate_session_id()
        
        if session_id in self.sessions:
            raise Exception(f"Session {session_id} existe déjà")
        
        session = SimulationSession(
            session_id=session_id,
            agent_configs=agent_configs,
            max_turns=max_turns,
            scenario=scenario
        )
        
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[SimulationSession]:
        """Récupère une session par son ID."""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """Supprime une session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """Liste tous les IDs de sessions."""
        return list(self.sessions.keys())
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Nettoie les sessions anciennes."""
        from datetime import timedelta
        
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
        removed = 0
        
        for session_id, session in list(self.sessions.items()):
            if session.last_activity and session.last_activity < cutoff:
                self.remove_session(session_id)
                removed += 1
        
        return removed



