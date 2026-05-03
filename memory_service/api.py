"""API REST pour le service mémoire."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .store import MemoryStore

logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title="LIA Memory Service",
    description="Service mémoire persistante pour LIA",
    version="0.1.0"
)

# Instance du store
store = MemoryStore()


# Modèles Pydantic pour les requêtes/réponses
class TraitCreate(BaseModel):
    type: str
    label: str
    value: str
    weight: float = 1.0
    confidence: float = 0.8


class MemoryCreate(BaseModel):
    category: str
    content: str
    tags: Optional[List[str]] = None
    importance_score: float = 0.5
    ttl_days: int = 30


class InteractionCreate(BaseModel):
    session_id: str
    prompt: str
    response: str
    scores: Optional[Dict[str, Any]] = None
    severity: str = "info"


@app.get("/")
async def root():
    """Endpoint racine."""
    return {"service": "LIA Memory Service", "version": "0.1.0"}


@app.get("/context")
async def get_context(
    limit_traits: int = 10,
    limit_memories: int = 10
) -> Dict[str, Any]:
    """
    Récupère le contexte mémoire (traits + souvenirs).
    
    Args:
        limit_traits: Nombre maximum de traits
        limit_memories: Nombre maximum de souvenirs
    
    Returns:
        Contexte avec traits, memories et session_goals
    """
    try:
        context = store.get_context(limit_traits, limit_memories)
        return context
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du contexte: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trait")
async def create_trait(trait: TraitCreate) -> Dict[str, Any]:
    """
    Crée ou met à jour un trait.
    
    Args:
        trait: Données du trait
    
    Returns:
        ID du trait créé/mis à jour
    """
    try:
        trait_id = store.add_trait(
            trait_type=trait.type,
            label=trait.label,
            value=trait.value,
            weight=trait.weight,
            confidence=trait.confidence
        )
        return {"trait_id": trait_id, "status": "created"}
    except Exception as e:
        logger.error(f"Erreur lors de la création du trait: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory")
async def create_memory(memory: MemoryCreate) -> Dict[str, Any]:
    """
    Crée un souvenir.
    
    Args:
        memory: Données du souvenir
    
    Returns:
        ID du souvenir créé
    """
    try:
        memory_id = store.add_memory(
            category=memory.category,
            content=memory.content,
            tags=memory.tags,
            importance_score=memory.importance_score,
            ttl_days=memory.ttl_days
        )
        return {"memory_id": memory_id, "status": "created"}
    except Exception as e:
        logger.error(f"Erreur lors de la création du souvenir: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interaction")
async def log_interaction(interaction: InteractionCreate) -> Dict[str, Any]:
    """
    Journalise une interaction.
    
    Args:
        interaction: Données de l'interaction
    
    Returns:
        ID de l'interaction journalisée
    """
    try:
        interaction_id = store.log_interaction(
            session_id=interaction.session_id,
            prompt=interaction.prompt,
            response=interaction.response,
            scores=interaction.scores,
            severity=interaction.severity
        )
        return {"interaction_id": interaction_id, "status": "logged"}
    except Exception as e:
        logger.error(f"Erreur lors de la journalisation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Vérification de santé du service."""
    return {"status": "healthy"}

