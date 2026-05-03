"""Recherche sémantique de haut niveau dans la mémoire.

Ce module fournit une interface simple pour effectuer des recherches
dans la mémoire en combinant similarité textuelle et MemoryRank V2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory_service.store import MemoryStore


class SemanticSearcher:
    """Recherche sémantique dans les phrases mémorisées."""

    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store

    def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        alpha: float = 0.6,
        beta: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Recherche sémantique.

        Processus :
        1. Segmenter la requête en phrases (implémentation simple via '.')
        2. Comparer avec les phrases mémorisées (délégué à MemoryStore)
        3. Calculer score = α·similarité + β·memory_rank (implémenté dans MemoryStore)
        4. Trier et retourner
        """
        query = (query or "").strip()
        if not query:
            return []

        # Pour l'instant, on délègue directement à MemoryStore.search_memories_semantic
        # qui gère la similarité et MemoryRank.
        return self.memory_store.search_memories_semantic(
            query=query,
            limit=limit,
            category=category,
            alpha=alpha,
            beta=beta,
        )



