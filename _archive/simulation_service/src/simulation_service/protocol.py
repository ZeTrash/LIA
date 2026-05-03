"""Protocole de communication inter-agents."""

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, UTC

import jsonschema
from pydantic import ValidationError

from .schemas import MultiAgentMessage, AgentHandshake, MessageType


# Charger les schémas JSON (simplifié - on utilise Pydantic pour la validation)
def validate_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valide un message selon le schéma JSON.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        MultiAgentMessage.model_validate(message)
        return True, None
    except ValidationError as e:
        return False, str(e)


def validate_handshake(handshake: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valide un handshake selon le schéma JSON.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        AgentHandshake.model_validate(handshake)
        return True, None
    except ValidationError as e:
        return False, str(e)


def serialize_message(message: MultiAgentMessage) -> str:
    """Sérialise un message en JSON."""
    return message.model_dump_json(exclude_none=True)


def deserialize_message(data: str) -> MultiAgentMessage:
    """Désérialise un message depuis JSON."""
    return MultiAgentMessage.model_validate_json(data)


def generate_message_id() -> str:
    """Génère un ID de message unique."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    unique_part = hashlib.md5(f"{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:3]
    return f"msg-{date_str}-{unique_part}"


def generate_session_id() -> str:
    """Génère un ID de session unique."""
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    unique_part = hashlib.md5(f"{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:3]
    return f"sim-{date_str}-{unique_part}"


def calculate_content_hash(content: str) -> str:
    """Calcule le hash SHA-256 du contenu d'un message."""
    return hashlib.sha256(content.encode()).hexdigest()


def detect_loop(messages: list[MultiAgentMessage], threshold: int = 3) -> bool:
    """
    Détecte si une boucle existe (messages identiques consécutifs).
    
    Args:
        messages: Liste des messages
        threshold: Nombre de messages identiques consécutifs pour détecter une boucle
        
    Returns:
        True si une boucle est détectée
    """
    if len(messages) < threshold:
        return False
    
    # Comparer les hash des contenus
    hashes = [calculate_content_hash(msg.content) for msg in messages[-threshold:]]
    
    # Vérifier si tous les hash sont identiques
    return len(set(hashes)) == 1



