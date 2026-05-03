"""Extensions avancées pour MemoryRank : hiérarchie fractale et intégration RL."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC
from enum import Enum

from sqlalchemy.orm import Session

from .models import SouvenirModel, MemoryLinkModel
from .memory_rank import MemoryRank
from .db import Database, get_db

logger = logging.getLogger(__name__)


class MemoryLevel(Enum):
    """Niveaux hiérarchiques de la mémoire fractale."""
    EVENT = "event"  # Événements individuels
    EPISODE = "episode"  # Épisodes (groupes d'événements)
    CONCEPT = "concept"  # Concepts abstraits
    OBJECTIVE = "objective"  # Objectifs/buts


class FractalMemoryRank:
    """MemoryRank avec hiérarchie fractale (événements → épisodes → concepts → objectifs)."""
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialise le système de mémoire fractale.
        
        Args:
            db: Instance de Database (optionnel)
        """
        self.db = db if db is not None else get_db()
        self.memory_rank = MemoryRank()
    
    def compute_hierarchical_ranks(
        self,
        level: MemoryLevel
    ) -> Dict[str, float]:
        """
        Calcule les scores MemoryRank pour un niveau hiérarchique spécifique.
        
        Args:
            level: Niveau hiérarchique (event, episode, concept, objective)
        
        Returns:
            Dictionnaire {memory_id: rank_score} pour ce niveau
        """
        session = self.db.get_session()
        try:
            # Récupérer les souvenirs du niveau spécifié
            # (on utilise les tags ou metadata pour identifier le niveau)
            memories = session.query(SouvenirModel).filter(
                SouvenirModel.ttl > datetime.now(UTC)
            ).all()
            
            # Filtrer par niveau (basé sur les tags ou category)
            level_memories = []
            for memory in memories:
                # Identifier le niveau basé sur les tags ou category
                memory_level = self._identify_memory_level(memory)
                if memory_level == level:
                    level_memories.append(memory)
            
            if not level_memories:
                return {}
            
            memory_ids = [m.memory_id for m in level_memories]
            
            # Récupérer les liens entre souvenirs de ce niveau
            links_query = session.query(MemoryLinkModel).filter(
                MemoryLinkModel.source_memory_id.in_(memory_ids),
                MemoryLinkModel.target_memory_id.in_(memory_ids)
            )
            links_data = links_query.all()
            links = [(link.source_memory_id, link.target_memory_id, link.weight) for link in links_data]
            
            # Calculer les rangs pour ce niveau
            ranks = self.memory_rank.compute_ranks(memory_ids, links)
            
            return ranks
        finally:
            session.close()
    
    def _identify_memory_level(self, memory: SouvenirModel) -> MemoryLevel:
        """
        Identifie le niveau hiérarchique d'un souvenir.
        
        Pour l'instant, on utilise une heuristique basée sur les tags et category.
        À améliorer avec un système de classification plus sophistiqué.
        """
        # Heuristique simple : utiliser les tags pour identifier le niveau
        if memory.tags:
            tags_lower = memory.tags.lower()
            if "objective" in tags_lower or "goal" in tags_lower:
                return MemoryLevel.OBJECTIVE
            elif "concept" in tags_lower or "abstract" in tags_lower:
                return MemoryLevel.CONCEPT
            elif "episode" in tags_lower or "session" in tags_lower:
                return MemoryLevel.EPISODE
        
        # Par défaut, considérer comme événement
        return MemoryLevel.EVENT
    
    def create_hierarchical_link(
        self,
        lower_level_id: str,
        higher_level_id: str,
        weight: float = 1.0
    ) -> str:
        """
        Crée un lien hiérarchique entre deux niveaux de mémoire.
        
        Args:
            lower_level_id: ID du souvenir de niveau inférieur
            higher_level_id: ID du souvenir de niveau supérieur
            weight: Poids du lien
        
        Returns:
            ID du lien créé
        """
        from .memory_rank_engine import MemoryRankEngine
        
        engine = MemoryRankEngine(db=self.db)
        return engine.add_link(
            source_memory_id=lower_level_id,
            target_memory_id=higher_level_id,
            weight=weight,
            link_type="hierarchical",
            metadata={"hierarchical": True}
        )
    
    def compute_all_levels_ranks(self) -> Dict[MemoryLevel, Dict[str, float]]:
        """
        Calcule les scores MemoryRank pour tous les niveaux hiérarchiques.
        
        Returns:
            Dictionnaire {level: {memory_id: rank_score}}
        """
        all_ranks = {}
        for level in MemoryLevel:
            ranks = self.compute_hierarchical_ranks(level)
            all_ranks[level] = ranks
            logger.info(f"MemoryRank calculé pour niveau {level.value}: {len(ranks)} souvenirs")
        
        return all_ranks


class RLMemoryRank:
    """Intégration MemoryRank avec récompenses RL."""
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialise l'intégration RL.
        
        Args:
            db: Instance de Database (optionnel)
        """
        self.db = db if db is not None else get_db()
        self.memory_rank = MemoryRank()
    
    def compute_hybrid_ranks(
        self,
        memory_ids: List[str],
        links: List[Tuple[str, str, float]],
        reward_scores: Dict[str, float],
        similarity_scores: Optional[Dict[str, float]] = None,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2
    ) -> Dict[str, float]:
        """
        Calcule des scores hybrides combinant MemoryRank, récompenses RL et similarité.
        
        Score = α * MemoryRank + β * Reward + γ * Similarité
        
        Args:
            memory_ids: Liste des IDs de souvenirs
            links: Liste de liens (source_id, target_id, weight)
            reward_scores: Dictionnaire {memory_id: reward_score}
            similarity_scores: Dictionnaire {memory_id: similarity_score} (optionnel)
            alpha: Poids pour MemoryRank
            beta: Poids pour Reward
            gamma: Poids pour Similarité
        
        Returns:
            Dictionnaire {memory_id: hybrid_score}
        """
        # Calculer les scores MemoryRank de base
        memory_ranks = self.memory_rank.compute_ranks(memory_ids, links)
        
        # Calculer les scores hybrides
        hybrid_scores = {}
        for memory_id in memory_ids:
            rank_score = memory_ranks.get(memory_id, 0.0)
            reward_score = reward_scores.get(memory_id, 0.0)
            similarity_score = similarity_scores.get(memory_id, 0.0) if similarity_scores else None
            
            hybrid_score = self.memory_rank.compute_hybrid_score(
                memory_rank=rank_score,
                reward_score=reward_score,
                similarity_score=similarity_score,
                alpha=alpha,
                beta=beta,
                gamma=gamma
            )
            hybrid_scores[memory_id] = hybrid_score
        
        return hybrid_scores
    
    def update_memory_with_reward(
        self,
        memory_id: str,
        reward: float,
        decay_factor: float = 0.9
    ) -> bool:
        """
        Met à jour un souvenir avec une récompense RL.
        
        Le score de récompense est stocké dans les métadonnées du souvenir
        et peut être utilisé pour le calcul hybride.
        
        Args:
            memory_id: ID du souvenir
            reward: Valeur de la récompense
            decay_factor: Facteur de décroissance pour les récompenses anciennes
        
        Returns:
            True si la mise à jour a réussi
        """
        session = self.db.get_session()
        try:
            memory = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == memory_id
            ).first()
            
            if not memory:
                logger.warning(f"Souvenir introuvable: {memory_id}")
                return False
            
            # Stocker la récompense dans importance_score ou dans un champ dédié
            # Pour l'instant, on utilise importance_score comme proxy
            # (dans une implémentation complète, on ajouterait un champ reward_score)
            current_importance = memory.importance_score
            # Mise à jour avec décroissance exponentielle
            new_importance = current_importance * decay_factor + reward * (1 - decay_factor)
            memory.importance_score = min(1.0, max(0.0, new_importance))
            memory.updated_at = datetime.now(UTC)
            
            session.commit()
            logger.debug(f"Récompense RL appliquée au souvenir {memory_id}: {reward}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la mise à jour avec récompense: {e}")
            return False
        finally:
            session.close()

