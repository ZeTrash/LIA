"""API FastAPI pour le service de simulation."""

from fastapi import Depends, FastAPI, HTTPException, Query, Header
from fastapi.security import APIKeyHeader
from typing import Optional

from .config import get_settings
from .orchestrator import SimulationOrchestrator
from .schemas import (
    SimulationStartRequest,
    SimulationStartResponse,
    MessageRequest,
    MessageResponse,
    SimulationStatus,
    SimulationStopResponse,
    SimulationExport,
    ErrorResponse,
    BehavioralMetrics
)
from .protocol import generate_message_id
from .metrics import calculate_all_metrics, calculate_metrics_by_agent


# Sécurité
api_key_header = APIKeyHeader(name="X-LIA-Token", auto_error=False)


def create_app() -> FastAPI:
    """Crée l'application FastAPI."""
    settings = get_settings()
    orchestrator = SimulationOrchestrator()
    
    app = FastAPI(
        title="LIA Simulation Multi-Agent Service",
        version="0.1.0",
        description="Service d'orchestration pour simulations multi-agents",
    )
    
    def get_orchestrator() -> SimulationOrchestrator:
        return orchestrator
    
    def verify_token(token: Optional[str] = Depends(api_key_header)) -> bool:
        """Vérifie le token d'authentification."""
        if settings.api_token and token != settings.api_token:
            raise HTTPException(status_code=401, detail="Token invalide")
        return True
    
    @app.get("/health", tags=["ops"])
    def health() -> dict:
        """Endpoint de santé."""
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment
        }
    
    @app.post(
        "/simulation/start",
        response_model=SimulationStartResponse,
        status_code=201,
        tags=["simulation"]
    )
    async def start_simulation(
        request: SimulationStartRequest,
        orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
        _: bool = Depends(verify_token)
    ) -> SimulationStartResponse:
        """Démarre une nouvelle simulation multi-agent."""
        try:
            session = await orchestrator.start_simulation(request)
            
            return SimulationStartResponse(
                session_id=session.session_id,
                status="running",
                agents=session.agent_ids,
                started_at=session.started_at
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={"error_code": "SIMULATION_START_FAILED", "message": str(e)}
            )
    
    @app.post(
        "/simulation/{session_id}/message",
        response_model=MessageResponse,
        tags=["simulation"]
    )
    async def send_message(
        session_id: str,
        request: MessageRequest,
        orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
        _: bool = Depends(verify_token)
    ) -> MessageResponse:
        """Envoie un message dans une simulation active."""
        try:
            response = await orchestrator.process_message(
                session_id=session_id,
                message_content=request.content,
                agent_id=request.agent_id
            )
            
            # Extraire le verdict de gouvernance
            governance_verdict = response.metadata.get("governance_verdict", "allow")
            
            return MessageResponse(
                message_id=response.message_id,
                response_content=response.content,
                response_agent_id=response.agent_id,
                turn=response.metadata.get("turn", 0),
                governance_verdict=governance_verdict
            )
        except Exception as e:
            error_msg = str(e)
            if "introuvable" in error_msg:
                raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": error_msg})
            elif "terminée" in error_msg:
                raise HTTPException(status_code=409, detail={"error_code": "SESSION_TERMINATED", "message": error_msg})
            else:
                raise HTTPException(status_code=400, detail={"error_code": "MESSAGE_FAILED", "message": error_msg})
    
    @app.get(
        "/simulation/{session_id}/status",
        response_model=SimulationStatus,
        tags=["simulation"]
    )
    async def get_simulation_status(
        session_id: str,
        orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
        _: bool = Depends(verify_token)
    ) -> SimulationStatus:
        """Récupère le statut d'une simulation."""
        session = orchestrator.get_session_status(session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "SESSION_NOT_FOUND", "message": f"Session {session_id} introuvable"}
            )
        
        return SimulationStatus(
            session_id=session.session_id,
            status=session.status,
            current_turn=session.current_turn,
            max_turns=session.max_turns,
            messages_count=len(session.messages),
            agents=session.agent_ids,
            metrics=session.metrics,
            started_at=session.started_at,
            last_activity=session.last_activity
        )
    
    @app.post(
        "/simulation/{session_id}/stop",
        response_model=SimulationStopResponse,
        tags=["simulation"]
    )
    async def stop_simulation(
        session_id: str,
        orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
        _: bool = Depends(verify_token)
    ) -> SimulationStopResponse:
        """Arrête une simulation et finalise la journalisation."""
        try:
            session = await orchestrator.stop_simulation(session_id)
            
            return SimulationStopResponse(
                session_id=session.session_id,
                status=session.status,
                stopped_at=session.last_activity or session.started_at,
                final_metrics=session.metrics,
                experience_id=session.experience_id
            )
        except Exception as e:
            if "introuvable" in str(e):
                raise HTTPException(status_code=404, detail={"error_code": "SESSION_NOT_FOUND", "message": str(e)})
            else:
                raise HTTPException(status_code=400, detail={"error_code": "STOP_FAILED", "message": str(e)})
    
    @app.get(
        "/simulation/{session_id}/export",
        response_model=SimulationExport,
        tags=["simulation"]
    )
    async def export_simulation(
        session_id: str,
        format: str = Query("json", pattern="^(json|csv)$"),
        orchestrator: SimulationOrchestrator = Depends(get_orchestrator),
        _: bool = Depends(verify_token)
    ) -> SimulationExport:
        """Exporte les résultats d'une simulation."""
        session = orchestrator.get_session_status(session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "SESSION_NOT_FOUND", "message": f"Session {session_id} introuvable"}
            )
        
        # Calculer les métriques si pas encore fait
        if not session.metrics and session.messages:
            session.metrics = calculate_all_metrics(session.messages)
        
        # Convertir les messages en dict pour l'export
        messages_data = [msg.model_dump(mode="json") for msg in session.messages]
        
        # Convertir metrics_by_agent en dict pour l'export
        metrics_by_agent_dict = {}
        if session.metrics_by_agent:
            for agent_id, metrics in session.metrics_by_agent.items():
                metrics_by_agent_dict[agent_id] = metrics.model_dump()
        
        return SimulationExport(
            session_id=session.session_id,
            started_at=session.started_at,
            ended_at=session.last_activity,
            agents=session.agent_ids,
            total_turns=session.current_turn,
            metrics=session.metrics,
            metrics_by_agent=metrics_by_agent_dict if metrics_by_agent_dict else None,
            messages=messages_data,
            experiences_created=[session.experience_id] if session.experience_id else [],
            traits_updated=[]  # TODO: Récupérer depuis memory_service
        )
    
    return app



