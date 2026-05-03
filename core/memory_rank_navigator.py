"""Navigation de haut niveau dans la mémoire basée sur MemoryRank.

Ce module fournit une couche simple au-dessus de `MemoryStore` pour :
- récupérer les souvenirs les plus importants,
- explorer les liens entre souvenirs,
- récupérer les traits les plus importants,
- accéder rapidement aux phrases d'identité.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory_service.store import MemoryStore


class MemoryRankNavigator:
    """Navigation intelligente dans la mémoire MemoryRank."""

    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store

    def get_top_memories(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        min_rank: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Récupère les souvenirs les plus importants (triés par MemoryRank)."""
        return self.memory_store.get_top_memories_by_rank(
            limit=limit,
            category=category,
            min_rank=min_rank,
        )

    def search_semantic(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        alpha: float = 0.6,
        beta: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Recherche sémantique dans la mémoire."""
        return self.memory_store.search_memories_semantic(
            query=query,
            limit=limit,
            category=category,
            alpha=alpha,
            beta=beta,
        )

    def get_connected_memories(
        self,
        memory_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Récupère les souvenirs liés (via MemoryRank links)."""
        return self.memory_store.get_memory_links(
            memory_id=memory_id,
            limit=limit,
        )

    def get_top_traits(
        self,
        limit: int = 10,
        trait_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Récupère les traits les plus importants."""
        return self.memory_store.get_top_traits_by_rank(
            limit=limit,
            trait_type=trait_type,
        )

    def get_identity_phrases(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Récupère les phrases d'identité les plus importantes.

        Implémentation simple : filtre sur la catégorie 'fact' avec tags/texte contenant 'identité'/'identity'.
        Cette logique pourra être raffinée plus tard (catégorie dédiée, tags structurés, etc.).
        """
        memories = self.memory_store.get_top_memories_by_rank(
            limit=100,  # récupérer un peu plus large puis filtrer
            category="fact",
            min_rank=0.0,
        )

        identity_candidates: List[Dict[str, Any]] = []
        for mem in memories:
            content = (mem.get("content") or "").lower()
            tags = [t.lower() for t in mem.get("tags") or []]
            if (
                "identité" in content
                or "identity" in content
                or "moi" in content
                or "qui je suis" in content
                or "identity" in tags
                or "identité" in tags
            ):
                identity_candidates.append(mem)

        # Déjà triés par MemoryRank, on tronque simplement
        return identity_candidates[:limit]



