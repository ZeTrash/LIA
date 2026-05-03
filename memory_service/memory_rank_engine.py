"""Moteur MemoryRank : service pour gérer le calcul et la mise à jour des scores MemoryRank."""

import logging
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import SouvenirModel, MemoryLinkModel
from .memory_rank import MemoryRank
from .db import Database, get_db

logger = logging.getLogger(__name__)


class MemoryRankEngine:
    """Moteur pour gérer le calcul et la mise à jour des scores MemoryRank."""
    
    def __init__(self, db: Optional[Database] = None, use_temporal_decay: bool = False, decay_factor: float = 0.01):
        """
        Initialise le moteur MemoryRank.
        
        Args:
            db: Instance de Database (optionnel, utilise get_db() par défaut)
            use_temporal_decay: Activer la décroissance temporelle
            decay_factor: Facteur de décroissance temporelle
        """
        self.db = db if db is not None else get_db()
        self.memory_rank = MemoryRank()
        self.use_temporal_decay = use_temporal_decay
        self.decay_factor = decay_factor
    
    def add_link(
        self,
        source_memory_id: str,
        target_memory_id: str,
        weight: float = 1.0,
        link_type: str = "cooccurrence",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Ajoute ou met à jour un lien entre deux souvenirs.
        
        Args:
            source_memory_id: ID du souvenir source
            target_memory_id: ID du souvenir cible
            weight: Poids du lien (force de référence)
            link_type: Type de lien (cooccurrence, similarity, citation, causal, etc.)
            metadata: Métadonnées additionnelles
        
        Returns:
            ID du lien créé ou mis à jour
        """
        session = self.db.get_session()
        try:
            # Vérifier que les souvenirs existent
            source = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == source_memory_id
            ).first()
            target = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id == target_memory_id
            ).first()
            
            if not source or not target:
                raise ValueError(f"Souvenirs introuvables: source={source_memory_id}, target={target_memory_id}")
            
            # Chercher un lien existant
            existing = session.query(MemoryLinkModel).filter(
                and_(
                    MemoryLinkModel.source_memory_id == source_memory_id,
                    MemoryLinkModel.target_memory_id == target_memory_id,
                    MemoryLinkModel.link_type == link_type
                )
            ).first()
            
            if existing:
                # Mettre à jour le poids (moyenne pondérée)
                existing.weight = (existing.weight + weight) / 2.0
                if metadata:
                    existing_metadata = existing.link_metadata or {}
                    existing_metadata.update(metadata)
                    existing.link_metadata = existing_metadata
                existing.updated_at = datetime.now(UTC)
                link_id = existing.link_id
            else:
                # Créer un nouveau lien
                link_id = str(uuid.uuid4())
                link = MemoryLinkModel(
                    link_id=link_id,
                    source_memory_id=source_memory_id,
                    target_memory_id=target_memory_id,
                    weight=weight,
                    link_type=link_type,
                    link_metadata=metadata,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                session.add(link)
            
            session.commit()
            logger.debug(f"Lien ajouté/mis à jour: {link_id} ({source_memory_id} -> {target_memory_id})")
            return link_id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout du lien: {e}")
            raise
        finally:
            session.close()
    
    def get_memory_graph(self, include_expired: bool = False) -> Tuple[List[str], List[Tuple[str, str, float]]]:
        """
        Récupère le graphe de mémoire (souvenirs + liens).
        
        Args:
            include_expired: Inclure les souvenirs expirés
        
        Returns:
            Tuple (memory_ids, links) où links est une liste de (source_id, target_id, weight)
        """
        session = self.db.get_session()
        try:
            # Récupérer tous les souvenirs actifs
            query = session.query(SouvenirModel)
            if not include_expired:
                query = query.filter(SouvenirModel.ttl > datetime.now(UTC))
            
            memories = query.all()
            memory_ids = [m.memory_id for m in memories]
            
            # Récupérer tous les liens entre ces souvenirs
            links_query = session.query(MemoryLinkModel).filter(
                and_(
                    MemoryLinkModel.source_memory_id.in_(memory_ids),
                    MemoryLinkModel.target_memory_id.in_(memory_ids)
                )
            )
            links_data = links_query.all()
            
            links = [(link.source_memory_id, link.target_memory_id, link.weight) for link in links_data]
            
            return memory_ids, links
        finally:
            session.close()
    
    def compute_and_update_ranks(self, force_recompute: bool = False) -> Dict[str, float]:
        """
        Calcule les scores MemoryRank et met à jour la base de données.
        
        Args:
            force_recompute: Forcer le recalcul même si les scores sont récents
        
        Returns:
            Dictionnaire {memory_id: rank_score} des scores calculés
        """
        session = self.db.get_session()
        try:
            # Récupérer le graphe
            memory_ids, links = self.get_memory_graph()
            
            if not memory_ids:
                logger.warning("Aucun souvenir trouvé pour calculer MemoryRank")
                return {}
            
            logger.info(f"Calcul MemoryRank pour {len(memory_ids)} souvenirs avec {len(links)} liens")
            
            # Calculer les rangs
            if self.use_temporal_decay:
                # Calculer les âges des souvenirs
                memory_ages = {}
                now = datetime.now(UTC)
                for memory_id in memory_ids:
                    memory = session.query(SouvenirModel).filter(
                        SouvenirModel.memory_id == memory_id
                    ).first()
                    if memory:
                        # S'assurer que created_at est timezone-aware
                        created_at = memory.created_at
                        if created_at.tzinfo is None:
                            # Si naive, supposer UTC
                            created_at = created_at.replace(tzinfo=UTC)
                        age_days = (now - created_at).total_seconds() / 86400.0
                        memory_ages[memory_id] = age_days
                
                ranks = self.memory_rank.compute_ranks_with_temporal_decay(
                    memory_ids, links, memory_ages, self.decay_factor
                )
            else:
                ranks = self.memory_rank.compute_ranks(memory_ids, links)
            
            # Mettre à jour les scores dans la base de données
            updated_count = 0
            for memory_id, rank_score in ranks.items():
                memory = session.query(SouvenirModel).filter(
                    SouvenirModel.memory_id == memory_id
                ).first()
                if memory:
                    memory.memory_rank_score = rank_score
                    memory.updated_at = datetime.now(UTC)
                    updated_count += 1
            
            session.commit()
            logger.info(f"MemoryRank mis à jour pour {updated_count} souvenirs")
            
            return ranks
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors du calcul MemoryRank: {e}")
            raise
        finally:
            session.close()
    
    def get_top_memories_by_rank(
        self,
        limit: int = 10,
        min_rank: float = 0.0,
        include_expired: bool = False
    ) -> List[SouvenirModel]:
        """
        Récupère les souvenirs avec les meilleurs scores MemoryRank.
        
        Args:
            limit: Nombre maximum de souvenirs à retourner
            min_rank: Score MemoryRank minimum
            include_expired: Inclure les souvenirs expirés
        
        Returns:
            Liste des souvenirs triés par MemoryRank décroissant
        """
        session = self.db.get_session()
        try:
            query = session.query(SouvenirModel).filter(
                SouvenirModel.memory_rank_score >= min_rank
            )
            
            if not include_expired:
                query = query.filter(SouvenirModel.ttl > datetime.now(UTC))
            
            memories = query.order_by(
                SouvenirModel.memory_rank_score.desc()
            ).limit(limit).all()
            
            return memories
        finally:
            session.close()
    
    def detect_cooccurrence_links(
        self,
        session_id: Optional[str] = None,
        lookback_days: int = 7
    ) -> int:
        """
        Détecte les co-occurrences de souvenirs dans les interactions récentes
        et crée des liens automatiquement.
        
        Args:
            session_id: ID de session spécifique (optionnel, toutes les sessions si None)
            lookback_days: Nombre de jours à regarder en arrière
        
        Returns:
            Nombre de liens créés
        """
        from .models import InteractionModel
        
        session = self.db.get_session()
        try:
            # Récupérer les interactions récentes
            cutoff_date = datetime.now(UTC) - timedelta(days=lookback_days)
            query = session.query(InteractionModel).filter(
                InteractionModel.occurred_at >= cutoff_date
            )
            
            if session_id:
                query = query.filter(InteractionModel.session_id == session_id)
            
            interactions = query.all()
            
            # Récupérer tous les souvenirs actifs
            memories = session.query(SouvenirModel).filter(
                SouvenirModel.ttl > datetime.now(UTC)
            ).all()
            
            # Créer un index de contenu -> memory_id pour recherche rapide
            content_to_memory = {}
            for memory in memories:
                # Normaliser le contenu pour la recherche
                content_lower = memory.content.lower()
                content_to_memory[content_lower] = memory.memory_id
                # Aussi indexer par tags si disponibles
                if memory.tags:
                    for tag in memory.tags.split(","):
                        tag_lower = tag.strip().lower()
                        if tag_lower:
                            if tag_lower not in content_to_memory:
                                content_to_memory[tag_lower] = memory.memory_id
            
            # Détecter les co-occurrences dans les interactions
            links_created = 0
            for interaction in interactions:
                # Chercher les souvenirs mentionnés dans le prompt et la réponse
                prompt_lower = interaction.prompt.lower()
                response_lower = interaction.response.lower()
                
                mentioned_memories = set()
                for content_key, memory_id in content_to_memory.items():
                    if content_key in prompt_lower or content_key in response_lower:
                        mentioned_memories.add(memory_id)
                
                # Créer des liens entre tous les souvenirs co-mentionnés
                mentioned_list = list(mentioned_memories)
                for i, mem_id_1 in enumerate(mentioned_list):
                    for mem_id_2 in mentioned_list[i+1:]:
                        try:
                            self.add_link(
                                source_memory_id=mem_id_1,
                                target_memory_id=mem_id_2,
                                weight=1.0,
                                link_type="cooccurrence",
                                metadata={"detected_from": interaction.interaction_id}
                            )
                            links_created += 1
                        except Exception as e:
                            logger.debug(f"Erreur lors de la création du lien de co-occurrence: {e}")
            
            logger.info(f"Détection de co-occurrences: {links_created} liens créés")
            return links_created
        finally:
            session.close()

