"""Orchestrateur des simulations multi-agents."""

import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime, UTC

from .schemas import (
    AgentConfig,
    MultiAgentMessage,
    SimulationStartRequest,
    SessionStatus,
    BehavioralMetrics
)
from .session import SessionManager, SimulationSession
from .adapters import AgentAdapter, create_adapter, LIAAdapter
from .metrics import calculate_all_metrics, calculate_metrics_by_agent
from .protocol import (
    generate_message_id,
    detect_loop,
    calculate_content_hash
)
from .config import get_settings


class SimulationOrchestrator:
    """Orchestrateur principal des simulations multi-agents."""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.adapters: Dict[str, AgentAdapter] = {}
        self.settings = get_settings()
    
    async def start_simulation(
        self,
        request: SimulationStartRequest
    ) -> SimulationSession:
        """Démarre une nouvelle simulation."""
        # Créer la session
        session = self.session_manager.create_session(
            agent_configs=request.agent_configs,
            max_turns=request.max_turns,
            scenario=request.scenario
        )
        
        # Créer les adapters pour chaque agent
        for config in request.agent_configs:
            adapter = create_adapter(config)
            self.adapters[config.agent_id] = adapter
            
            # Effectuer le handshake
            try:
                handshake = await adapter.perform_handshake()
                # Valider le handshake
                from .protocol import validate_handshake
                is_valid, error = validate_handshake(handshake)
                if not is_valid:
                    raise Exception(f"Handshake invalide pour {config.agent_id}: {error}")
            except Exception as e:
                session.status = "failed"
                raise Exception(f"Erreur handshake pour {config.agent_id}: {e}")
        
        # Récupérer les traits initiaux pour chaque agent LIA
        for agent_id, adapter in self.adapters.items():
            if isinstance(adapter, LIAAdapter):
                try:
                    traits = await adapter.get_traits(session.session_id)
                    session.initial_traits[agent_id] = {
                        trait.get("trait_id"): trait for trait in traits
                    }
                except Exception:
                    pass  # Ignorer les erreurs
        
        # Créer l'Experience dans memory_service
        session.experience_id = f"exp-sim-{session.session_id}"
        for agent_id, adapter in self.adapters.items():
            if isinstance(adapter, LIAAdapter):
                try:
                    await adapter.create_experience(
                        experience_id=session.experience_id,
                        title=f"Simulation multi-agent {session.session_id}",
                        session_id=session.session_id,
                        started_at=session.started_at.isoformat()
                    )
                    break  # Créer l'Experience une seule fois
                except Exception:
                    pass  # Ignorer les erreurs
        
        session.status = "running"
        return session
    
    async def process_message(
        self,
        session_id: str,
        message_content: str,
        agent_id: Optional[str] = None
    ) -> MultiAgentMessage:
        """
        Traite un message dans une simulation.
        
        Si agent_id est None, utilise le prochain agent dans la rotation.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise Exception(f"Session {session_id} introuvable")
        
        if session.is_complete():
            raise Exception(f"Session {session_id} est terminée")
        
        # Déterminer l'agent émetteur
        if agent_id is None:
            agent_id = session.get_next_agent_id()
        
        if agent_id not in self.adapters:
            raise Exception(f"Adapter pour {agent_id} introuvable")
        
        adapter = self.adapters[agent_id]
        partner_id = session.get_partner_agent_id(agent_id)
        
        if not partner_id or partner_id not in self.adapters:
            raise Exception(f"Adapter pour l'agent partenaire {partner_id} introuvable")
        
        partner_adapter = self.adapters[partner_id]
        
        if not partner_id:
            raise Exception(f"Agent partenaire introuvable pour {agent_id}")
        
        # Créer le message
        turn = session.current_turn + 1
        message = MultiAgentMessage(
            message_id=generate_message_id(),
            session_id=session_id,
            agent_id=agent_id,
            agent_partner_id=partner_id,
            timestamp=datetime.now(UTC),
            message_type="text",
            content=message_content,
            metadata={
                "turn": turn,
                "context_used": agent_id.startswith("lia-")
            }
        )
        
            # Envoyer le message à l'agent partenaire
        try:
            # Récupérer le contexte si nécessaire (pour LIA)
            context = None
            partner_adapter = self.adapters.get(partner_id)
            if partner_adapter and isinstance(partner_adapter, LIAAdapter):
                # Récupérer le contexte depuis memory_service
                context = await partner_adapter.get_context(session_id)
            
            # Appel avec timeout
            response_content = await asyncio.wait_for(
                partner_adapter.send_message(
                    message_content,
                    context=context,
                    session_id=session_id
                ),
                timeout=self.settings.default_timeout_seconds
            )
            
            # Créer la réponse
            response = MultiAgentMessage(
                message_id=generate_message_id(),
                session_id=session_id,
                agent_id=partner_id,
                agent_partner_id=agent_id,
                timestamp=datetime.now(UTC),
                message_type="text",
                content=response_content,
                metadata={
                    "turn": turn,
                    "context_used": partner_id.startswith("lia-")
                }
            )
            
            # Vérifier la gouvernance (pour LIA)
            if partner_adapter and isinstance(partner_adapter, LIAAdapter):
                governance_result = await partner_adapter.check_governance(session_id, response_content)
                governance_verdict = governance_result.get("verdict", "allow")
                response.metadata["governance_verdict"] = governance_verdict
                
                if governance_verdict == "block":
                    session.status = "stopped"
                    raise Exception("Message bloqué par la gouvernance")
            else:
                governance_verdict = "allow"
                response.metadata["governance_verdict"] = governance_verdict
            
            # Ajouter les messages à la session
            session.add_message(message)
            session.add_message(response)
            
            # Détecter les boucles
            if detect_loop(session.messages[-3:], threshold=3):
                session.loop_detected = True
                session.status = "stopped"
                raise Exception("Boucle détectée")
            
            # Vérifier les limites
            if session.current_turn >= session.max_turns:
                session.status = "completed"
            
            return response
        
        except asyncio.TimeoutError:
            session.timeout_count += 1
            if session.timeout_count >= 3:
                session.status = "failed"
                raise Exception("Trop de timeouts consécutifs")
            raise Exception("Timeout lors de l'envoi du message")
        
        except Exception as e:
            session.error_count += 1
            if session.error_count >= 5:
                session.status = "failed"
            raise
    
    async def stop_simulation(self, session_id: str) -> SimulationSession:
        """Arrête une simulation et calcule les métriques finales."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise Exception(f"Session {session_id} introuvable")
        
        if session.status == "running":
            session.status = "stopped"
        
        # Calculer les métriques finales
        if session.messages:
            # Métriques globales
            session.metrics = calculate_all_metrics(session.messages)
            
            # Métriques par agent
            session.metrics_by_agent = calculate_metrics_by_agent(
                session.messages,
                session.agent_ids,
                initial_traits=session.initial_traits
            )
            
            # Finaliser l'Experience dans memory_service
            if session.experience_id:
                for agent_id, adapter in self.adapters.items():
                    if isinstance(adapter, LIAAdapter):
                        try:
                            # Récupérer les IDs des souvenirs créés pendant la simulation
                            related_memories = []
                            # TODO: Récupérer les IDs depuis les interactions loggées
                            
                            await adapter.finalize_experience(
                                experience_id=session.experience_id,
                                session_id=session.session_id,
                                ended_at=session.last_activity.isoformat() if session.last_activity else session.started_at.isoformat(),
                                metrics_snapshot=session.metrics.model_dump() if session.metrics else None,
                                related_memories=related_memories
                            )
                            break  # Finaliser l'Experience une seule fois
                        except Exception:
                            pass  # Ignorer les erreurs
        
        return session
    
    def get_session_status(self, session_id: str) -> Optional[SimulationSession]:
        """Récupère le statut d'une session."""
        return self.session_manager.get_session(session_id)
    
    async def cleanup(self):
        """Nettoie les ressources (ferme les adapters, etc.)."""
        for adapter in self.adapters.values():
            if hasattr(adapter, '__aexit__'):
                await adapter.__aexit__(None, None, None)
        
        self.adapters.clear()



