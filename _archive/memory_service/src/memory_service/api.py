"""Application FastAPI exposant le service mémoire."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query, Response

from .config import get_settings
from .db import create_session_factory
from .metrics import export_prometheus
from .schemas import (
    ContextResponse,
    GovernanceCheckRequest,
    GovernanceCheckResponse,
    InteractionLog,
    InteractionRequest,
    MetricsResponse,
    PersonalGoal,
    PersonalGoalCreate,
    PersonalGoalUpdate,
    TraitUpdateRequest,
    TraitUpdateResponse,
)
from .store import MemoryStore


def create_app() -> FastAPI:
    settings = get_settings()
    session_factory = create_session_factory(settings)
    store = MemoryStore(settings, session_factory)

    app = FastAPI(
        title="Memory Service",
        version="0.1.0",
        description="Couche mémoire locale pour le moteur LLM.",
    )

    def get_store() -> MemoryStore:
        return store

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    @app.get("/context", response_model=ContextResponse, tags=["context"])
    def read_context(
        session_id: str = Query(..., description="Identifiant de session LLM"),
        max_memories: int | None = Query(None, ge=1, le=24),
        store: MemoryStore = Depends(get_store),
    ) -> ContextResponse:
        return store.get_context(session_id=session_id, max_memories=max_memories)

    @app.post("/interaction", response_model=InteractionLog, tags=["interaction"])
    def post_interaction(
        payload: InteractionRequest,
        store: MemoryStore = Depends(get_store),
    ) -> InteractionLog:
        return store.log_interaction(payload)

    @app.post("/trait-update", response_model=TraitUpdateResponse, tags=["traits"])
    def post_trait_update(
        payload: TraitUpdateRequest,
        store: MemoryStore = Depends(get_store),
    ) -> TraitUpdateResponse:
        from .schemas import Trait
        response = store.update_trait(payload)
        if payload.expected_version and response.review_required:
            # Erreur 409 avec latest_trait selon OpenAPI
            raise HTTPException(
                status_code=409,
                detail={"error_code": "VERSION_CONFLICT", "message": "Version du trait obsolète"},
                headers={"X-Trait-Version": str(response.trait.version)}
            )
        return response

    @app.post("/governance/check", response_model=GovernanceCheckResponse, tags=["governance"])
    def post_governance_check(
        payload: GovernanceCheckRequest,
        store: MemoryStore = Depends(get_store),
    ) -> GovernanceCheckResponse:
        return store.check_governance(payload)

    @app.get("/metrics", response_model=MetricsResponse, tags=["observability"])
    def read_metrics(
        store: MemoryStore = Depends(get_store),
    ) -> MetricsResponse:
        return store.get_metrics()

    @app.get("/metrics/prom", tags=["observability"])
    def read_metrics_prometheus() -> Response:
        payload, content_type = export_prometheus()
        return Response(content=payload, media_type=content_type)

    # ------------------------------------------------------------------
    # Personal Goals Endpoints (Étape 2.6)
    # ------------------------------------------------------------------
    @app.post("/personal-goals", response_model=PersonalGoal, status_code=201, tags=["personal-goals"])
    def create_personal_goal(
        payload: PersonalGoalCreate,
        store: MemoryStore = Depends(get_store),
    ) -> PersonalGoal:
        """Crée un nouvel objectif personnel."""
        return store.create_personal_goal(payload)

    @app.get("/personal-goals", response_model=list[PersonalGoal], tags=["personal-goals"])
    def get_personal_goals(
        status: str | None = Query(None, description="Filtrer par statut"),
        goal_type: str | None = Query(None, description="Filtrer par type"),
        store: MemoryStore = Depends(get_store),
    ) -> list[PersonalGoal]:
        """Récupère la liste des objectifs personnels avec filtres optionnels."""
        return store.get_personal_goals(status=status, goal_type=goal_type)

    @app.get("/personal-goals/{goal_id}", response_model=PersonalGoal, tags=["personal-goals"])
    def get_personal_goal(
        goal_id: str,
        store: MemoryStore = Depends(get_store),
    ) -> PersonalGoal:
        """Récupère un objectif personnel par ID."""
        goal = store.get_personal_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Objectif {goal_id} introuvable")
        return goal

    @app.put("/personal-goals/{goal_id}", response_model=PersonalGoal, tags=["personal-goals"])
    def update_personal_goal(
        goal_id: str,
        payload: PersonalGoalUpdate,
        store: MemoryStore = Depends(get_store),
    ) -> PersonalGoal:
        """Met à jour un objectif personnel."""
        goal = store.update_personal_goal(goal_id, payload)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Objectif {goal_id} introuvable")
        return goal

    @app.delete("/personal-goals/{goal_id}", status_code=204, tags=["personal-goals"])
    def delete_personal_goal(
        goal_id: str,
        store: MemoryStore = Depends(get_store),
    ) -> None:
        """Supprime un objectif personnel."""
        if not store.delete_personal_goal(goal_id):
            raise HTTPException(status_code=404, detail=f"Objectif {goal_id} introuvable")

    return app



