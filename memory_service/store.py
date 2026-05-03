"""Logique métier pour le service mémoire."""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from .models import TraitModel, SouvenirModel, InteractionModel, PatternModel, ThemePatternModel, MemoryLinkModel
from .db import get_db, Database
from .memory_rank_engine import MemoryRankEngine

logger = logging.getLogger(__name__)


class MemoryStore:
    """Store pour la gestion de la mémoire."""
    
    def __init__(self, db: Optional[Database] = None, use_memory_rank: bool = True):
        """
        Initialise le store.
        
        Args:
            db: Instance de Database à utiliser (optionnel, utilise get_db() par défaut)
            use_memory_rank: Utiliser MemoryRank pour trier les souvenirs (par défaut: True)
        """
        self.db = db if db is not None else get_db()
        self.use_memory_rank = use_memory_rank
        self.memory_rank_engine = MemoryRankEngine(db=self.db) if use_memory_rank else None
    
    def get_context(self, limit_traits: int = 10, limit_memories: int = 10, limit_interactions: int = 5) -> Dict[str, Any]:
        """
        Récupère le contexte mémoire (traits + souvenirs + historique de conversation).
        
        Args:
            limit_traits: Nombre maximum de traits à retourner
            limit_memories: Nombre maximum de souvenirs à retourner
            limit_interactions: Nombre maximum d'interactions récentes à retourner
        
        Returns:
            Dictionnaire avec traits, memories et recent_interactions
        """
        session = self.db.get_session()
        try:
            # Récupérer les traits actifs
            traits = session.query(TraitModel).filter(
                TraitModel.status == "active"
            ).order_by(desc(TraitModel.last_update)).limit(limit_traits).all()
            
            # Récupérer les souvenirs les plus importants
            # Utiliser MemoryRank si activé, sinon utiliser l'ancien système
            if self.use_memory_rank and self.memory_rank_engine:
                try:
                    # S'assurer que les scores MemoryRank sont à jour
                    # (on peut optimiser en vérifiant la dernière mise à jour)
                    self.memory_rank_engine.compute_and_update_ranks()
                    
                    # Récupérer les souvenirs triés par MemoryRank
                    memories = self.memory_rank_engine.get_top_memories_by_rank(
                        limit=limit_memories,
                        include_expired=False
                    )
                except Exception as e:
                    logger.warning(f"Erreur lors de l'utilisation de MemoryRank, fallback sur l'ancien système: {e}")
                    # Fallback sur l'ancien système
                    memories = session.query(SouvenirModel).filter(
                        SouvenirModel.ttl > datetime.now(UTC)
                    ).order_by(
                        desc(SouvenirModel.importance_score),
                        desc(SouvenirModel.recency_score)
                    ).limit(limit_memories).all()
            else:
                # Ancien système : tri par importance_score et recency_score
                memories = session.query(SouvenirModel).filter(
                    SouvenirModel.ttl > datetime.now(UTC)
                ).order_by(
                    desc(SouvenirModel.importance_score),
                    desc(SouvenirModel.recency_score)
                ).limit(limit_memories).all()
            
            # Récupérer les dernières interactions (peu importe la session)
            recent_interactions = session.query(InteractionModel).order_by(
                desc(InteractionModel.occurred_at)
            ).limit(limit_interactions).all()
            
            return {
                "traits": [
                    {
                        "trait_id": t.trait_id,
                        "type": t.type,
                        "label": t.label,
                        "value": t.value,
                        "weight": t.weight,
                        "confidence": t.confidence
                    }
                    for t in traits
                ],
                "memories": [
                    {
                        "memory_id": m.memory_id,
                        "category": m.category,
                        "content": m.content,
                        "tags": m.tags.split(",") if m.tags else [],
                        "importance_score": m.importance_score,
                        "recency_score": m.recency_score,
                        "memory_rank_score": getattr(m, 'memory_rank_score', 0.0)  # Score MemoryRank si disponible
                    }
                    for m in memories
                ],
                "recent_interactions": [
                    {
                        "interaction_id": i.interaction_id,
                        "session_id": i.session_id,
                        "prompt": i.prompt,
                        "response": i.response,
                        "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None
                    }
                    for i in recent_interactions
                ],
                "session_goals": []  # Pour l'instant vide
            }
        finally:
            session.close()
    
    def add_trait(
        self,
        trait_type: str,
        label: str,
        value: str,
        weight: float = 1.0,
        confidence: float = 0.8
    ) -> str:
        """
        Ajoute ou met à jour un trait.
        
        Args:
            trait_type: Type de trait (persona, skill, style, constraint)
            label: Label du trait
            value: Valeur du trait
            weight: Poids du trait
            confidence: Confiance dans le trait
        
        Returns:
            ID du trait
        """
        session = self.db.get_session()
        try:
            # Chercher un trait existant avec le même label
            existing = session.query(TraitModel).filter(
                TraitModel.label == label,
                TraitModel.type == trait_type
            ).first()
            
            if existing:
                # Mettre à jour
                existing.value = value
                existing.weight = weight
                existing.confidence = confidence
                existing.version += 1
                existing.last_update = datetime.now(UTC)
                trait_id = existing.trait_id
            else:
                # Créer nouveau
                trait_id = str(uuid.uuid4())
                trait = TraitModel(
                    trait_id=trait_id,
                    type=trait_type,
                    label=label,
                    value=value,
                    weight=weight,
                    confidence=confidence,
                    version=1,
                    status="active"
                )
                session.add(trait)
            
            session.commit()
            logger.info(f"Trait ajouté/mis à jour: {trait_id} ({label})")
            return trait_id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout du trait: {e}")
            raise
        finally:
            session.close()
    
    def add_memory(
        self,
        category: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance_score: float = 0.5,
        ttl_days: int = 30
    ) -> str:
        """
        Ajoute un souvenir.
        
        Args:
            category: Catégorie (fact, preference, alert)
            content: Contenu du souvenir
            tags: Tags associés
            importance_score: Score d'importance (0.0 - 1.0)
            ttl_days: Durée de vie en jours
        
        Returns:
            ID du souvenir
        """
        session = self.db.get_session()
        try:
            memory_id = str(uuid.uuid4())
            ttl = datetime.now(UTC) + timedelta(days=ttl_days)
            
            memory = SouvenirModel(
                memory_id=memory_id,
                category=category,
                content=content,
                tags=",".join(tags) if tags else None,
                importance_score=importance_score,
                recency_score=1.0,  # Nouveau souvenir = récent
                frequency=1,
                ttl=ttl
            )
            
            session.add(memory)
            session.commit()
            logger.info(f"Souvenir ajouté: {memory_id} ({category})")
            return memory_id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout du souvenir: {e}")
            raise
        finally:
            session.close()
    
    def add_memory_link(
        self,
        source_memory_id: str,
        target_memory_id: str,
        weight: float = 1.0,
        link_type: str = "cooccurrence",
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Ajoute un lien entre deux souvenirs (pour MemoryRank).
        
        Args:
            source_memory_id: ID du souvenir source
            target_memory_id: ID du souvenir cible
            weight: Poids du lien
            link_type: Type de lien (cooccurrence, similarity, citation, causal, etc.)
            metadata: Métadonnées additionnelles
        
        Returns:
            ID du lien créé ou None en cas d'erreur
        """
        if not self.memory_rank_engine:
            logger.warning("MemoryRank non activé, impossible d'ajouter un lien")
            return None
        
        try:
            return self.memory_rank_engine.add_link(
                source_memory_id=source_memory_id,
                target_memory_id=target_memory_id,
                weight=weight,
                link_type=link_type,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du lien mémoire: {e}")
            return None
    
    def update_memory_ranks(self) -> Dict[str, float]:
        """
        Met à jour les scores MemoryRank pour tous les souvenirs.
        
        Returns:
            Dictionnaire {memory_id: rank_score} des scores calculés
        """
        if not self.memory_rank_engine:
            logger.warning("MemoryRank non activé, impossible de mettre à jour les scores")
            return {}
        
        try:
            return self.memory_rank_engine.compute_and_update_ranks()
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des scores MemoryRank: {e}")
            return {}

    # ---------------------------------------------------------------------
    # Patterns (Phase "seed" / puis apprentissage Gemini)
    # ---------------------------------------------------------------------

    def list_theme_patterns(self) -> List[str]:
        """Retourne la liste des noms de thèmes disponibles (V2)."""
        session = self.db.get_session()
        try:
            themes = session.query(ThemePatternModel.theme_name).all()
            return [t[0] for t in themes]
        finally:
            session.close()

    def get_theme_examples(self, limit_per_theme: int = 2) -> Dict[str, List[Dict[str, Any]]]:
        """Retourne des exemples de patterns par thème pour enrichir le prompt de classification.
        
        Args:
            limit_per_theme: Nombre d'exemples maximum par thème
        
        Returns:
            Dict {theme_name: [patterns]} où chaque pattern contient menu_context, prev_step, recommended_step
        """
        session = self.db.get_session()
        try:
            themes = self.list_theme_patterns()
            examples: Dict[str, List[Dict[str, Any]]] = {}
            
            for theme in themes:
                patterns = (
                    session.query(PatternModel)
                    .filter(PatternModel.theme_pattern == theme)
                    .order_by(PatternModel.updated_at.desc())
                    .limit(limit_per_theme)
                    .all()
                )
                examples[theme] = [
                    {
                        "menu_context": p.menu_context,
                        "prev_step": p.prev_step,
                        "recommended_step": p.recommended_step,
                    }
                    for p in patterns
                ]
            
            return examples
        finally:
            session.close()

    def add_theme_pattern(self, theme_name: str) -> str:
        """Ajoute un thème s'il n'existe pas. Retourne l'ID du thème."""
        # Nettoyer les guillemets et espaces
        theme_name = (theme_name or "").strip().strip('"\'')
        if not theme_name:
            raise ValueError("theme_name must be non-empty")
        session = self.db.get_session()
        try:
            existing = session.query(ThemePatternModel).filter(
                ThemePatternModel.theme_name == theme_name
            ).first()
            if existing:
                logger.debug(f"🧩 Theme pattern déjà existant: {theme_name} (id={existing.theme_id})")
                return existing.theme_id
            theme_id = str(uuid.uuid4())
            t = ThemePatternModel(
                theme_id=theme_id,
                theme_name=theme_name,
                created_at=datetime.now(UTC),
            )
            session.add(t)
            session.commit()
            logger.info(f"🧩 Theme pattern ajouté: {theme_name} (id={theme_id})")
            return theme_id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout du theme pattern: {e}")
            raise
        finally:
            session.close()

    def upsert_pattern(
        self,
        menu_context: str,
        prev_step: str,
        recommended_step: str,
        weights: Optional[Dict[str, float]] = None,
        source: str = "seed",
        confidence: float = 0.5,
        theme_pattern: Optional[str] = None,
    ) -> str:
        """Crée ou met à jour une recommandation de pattern.

        Clé logique: (theme_pattern?, menu_context, prev_step).
        """
        menu_context = (menu_context or "").strip() or "unknown"
        prev_step = (prev_step or "").strip() or "initial"
        recommended_step = (recommended_step or "").strip()
        if not recommended_step:
            raise ValueError("recommended_step must be non-empty")
        theme_pattern = (theme_pattern or "").strip() or None

        session = self.db.get_session()
        try:
            q = session.query(PatternModel).filter(
                PatternModel.menu_context == menu_context,
                PatternModel.prev_step == prev_step,
            )
            if theme_pattern is not None:
                q = q.filter(PatternModel.theme_pattern == theme_pattern)
            else:
                q = q.filter((PatternModel.theme_pattern.is_(None)) | (PatternModel.theme_pattern == ""))
            existing = q.first()

            if existing:
                existing.recommended_step = recommended_step

                # Fusion des poids (si fournis) avec les poids existants :
                # - On fait une moyenne simple old/new puis on renormalise pour que la somme = 1.0.
                if weights is not None:
                    old_weights = existing.weights or {}
                    new_weights = {}
                    all_keys = set(old_weights.keys()) | set(weights.keys())
                    for k in all_keys:
                        v_old = float(old_weights.get(k, 0.0) or 0.0)
                        v_new = float(weights.get(k, 0.0) or 0.0)
                        new_weights[k] = (v_old + v_new) / 2.0
                    total = sum(new_weights.values())
                    if total > 0:
                        for k in list(new_weights.keys()):
                            new_weights[k] = new_weights[k] / total
                    existing.weights = new_weights

                existing.source = source or existing.source
                existing.confidence = float(confidence)
                existing.updated_at = datetime.now(UTC)
                pattern_id = existing.pattern_id
            else:
                pattern_id = str(uuid.uuid4())
                p = PatternModel(
                    pattern_id=pattern_id,
                    theme_pattern=theme_pattern,
                    menu_context=menu_context,
                    prev_step=prev_step,
                    recommended_step=recommended_step,
                    weights=weights or None,
                    source=source,
                    confidence=float(confidence),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(p)

            session.commit()
            # Log détaillé pour suivi des patterns (SYSTEME_PATTERNS)
            safe_weights = (existing.weights if existing else weights) or {}
            logger.info(
                "🧩 Pattern upsert: "
                f"id={pattern_id}, theme={theme_pattern or 'global'}, ctx={menu_context}, prev={prev_step}, "
                f"rec={recommended_step}, conf={confidence}, "
                f"weights={safe_weights}"
            )
            return pattern_id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'upsert pattern: {e}")
            raise
        finally:
            session.close()

    def get_pattern_recommendation(
        self,
        menu_context: str,
        prev_step: str,
        theme_pattern: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Récupère une recommandation de pattern (si disponible).

        Si theme_pattern est fourni, cherche d'abord un pattern spécifique au thème,
        sinon fallback sur le pattern global (sans thème).
        """
        menu_context = (menu_context or "").strip() or "unknown"
        prev_step = (prev_step or "").strip() or "initial"
        theme_pattern = (theme_pattern or "").strip() or None

        session = self.db.get_session()
        try:
            # Essayer d'abord le pattern spécifique au thème
            if theme_pattern:
                p = (
                    session.query(PatternModel)
                    .filter(
                        PatternModel.menu_context == menu_context,
                        PatternModel.prev_step == prev_step,
                        PatternModel.theme_pattern == theme_pattern,
                    )
                    .first()
                )
                if p:
                    return {
                        "pattern_id": p.pattern_id,
                        "theme_pattern": p.theme_pattern,
                        "menu_context": p.menu_context,
                        "prev_step": p.prev_step,
                        "recommended_step": p.recommended_step,
                        "weights": p.weights or {},
                        "source": p.source,
                        "confidence": float(p.confidence or 0.0),
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    }
            # Fallback : pattern global (sans thème)
            p = (
                session.query(PatternModel)
                .filter(
                    PatternModel.menu_context == menu_context,
                    PatternModel.prev_step == prev_step,
                )
                .filter(
                    (PatternModel.theme_pattern.is_(None)) | (PatternModel.theme_pattern == "")
                )
                .first()
            )
            if not p:
                return None
            return {
                "pattern_id": p.pattern_id,
                "theme_pattern": p.theme_pattern,
                "menu_context": p.menu_context,
                "prev_step": p.prev_step,
                "recommended_step": p.recommended_step,
                "weights": p.weights or {},
                "source": p.source,
                "confidence": float(p.confidence or 0.0),
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        finally:
            session.close()
    
    def log_interaction(
        self,
        session_id: str,
        prompt: str,
        response: str,
        scores: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ) -> str:
        """
        Journalise une interaction.
        
        Args:
            session_id: ID de session
            prompt: Prompt de l'utilisateur
            response: Réponse générée
            scores: Scores optionnels
            severity: Sévérité (info, warning, error)
        
        Returns:
            ID de l'interaction
        """
        session = self.db.get_session()
        try:
            interaction_id = str(uuid.uuid4())
            
            interaction = InteractionModel(
                interaction_id=interaction_id,
                session_id=session_id,
                prompt=prompt,
                response=response,
                scores=scores,
                severity=severity,
                occurred_at=datetime.now(UTC)
            )
            
            session.add(interaction)
            session.commit()
            logger.info(f"Interaction journalisée: {interaction_id}")
            return interaction_id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la journalisation: {e}")
            raise
        finally:
            session.close()
    
    def get_top_memories_by_rank(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        min_rank: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Récupère les souvenirs triés par MemoryRank.
        
        Args:
            limit: Nombre maximum de souvenirs à retourner
            category: Filtrer par catégorie (optionnel)
            min_rank: Score MemoryRank minimum (défaut: 0.0)
        
        Returns:
            Liste de dictionnaires contenant les souvenirs triés par MemoryRank
        """
        session = self.db.get_session()
        try:
            query = session.query(SouvenirModel).filter(
                SouvenirModel.memory_rank_score >= min_rank,
                SouvenirModel.ttl > datetime.now(UTC)
            )
            
            if category:
                query = query.filter(SouvenirModel.category == category)
            
            memories = query.order_by(
                desc(SouvenirModel.memory_rank_score)
            ).limit(limit).all()
            
            return [self._memory_to_dict(m) for m in memories]
        finally:
            session.close()
    
    def get_memory_links(
        self,
        memory_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Récupère les souvenirs liés via MemoryRank.
        
        Retourne les souvenirs connectés, triés par poids de lien + MemoryRank.
        
        Args:
            memory_id: ID du souvenir source
            limit: Nombre maximum de souvenirs liés à retourner
        
        Returns:
            Liste de dictionnaires contenant les souvenirs liés avec leurs poids de lien
        """
        session = self.db.get_session()
        try:
            # Récupérer les liens sortants
            links = session.query(MemoryLinkModel).filter(
                MemoryLinkModel.source_memory_id == memory_id
            ).order_by(
                desc(MemoryLinkModel.weight)
            ).limit(limit).all()
            
            if not links:
                return []
            
            # Récupérer les souvenirs cibles
            target_ids = [l.target_memory_id for l in links]
            memories = session.query(SouvenirModel).filter(
                SouvenirModel.memory_id.in_(target_ids)
            ).all()
            
            # Créer dict avec poids de lien
            memory_dict = {m.memory_id: self._memory_to_dict(m) for m in memories}
            result = []
            for link in links:
                if link.target_memory_id in memory_dict:
                    mem = memory_dict[link.target_memory_id].copy()
                    mem['link_weight'] = link.weight
                    mem['link_type'] = link.link_type
                    result.append(mem)
            
            # Trier par poids de lien + MemoryRank
            result.sort(
                key=lambda x: (
                    x.get('link_weight', 0.0),
                    x.get('memory_rank_score', 0.0)
                ),
                reverse=True
            )
            
            return result[:limit]
        finally:
            session.close()
    
    def get_top_traits_by_rank(
        self,
        limit: int = 10,
        trait_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les traits triés par poids (utilisé comme proxy de MemoryRank).
        
        Args:
            limit: Nombre maximum de traits à retourner
            trait_type: Filtrer par type de trait (optionnel)
        
        Returns:
            Liste de dictionnaires contenant les traits triés par poids
        """
        session = self.db.get_session()
        try:
            query = session.query(TraitModel).filter(
                TraitModel.status == "active"
            )
            
            if trait_type:
                query = query.filter(TraitModel.type == trait_type)
            
            traits = query.order_by(
                desc(TraitModel.weight)
            ).limit(limit).all()
            
            return [self._trait_to_dict(t) for t in traits]
        finally:
            session.close()
    
    def search_memories_semantic(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        alpha: float = 0.6,
        beta: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique dans les souvenirs.
        
        Score final = α·similarité + β·memory_rank
        
        Args:
            query: Requête de recherche
            limit: Nombre maximum de résultats
            category: Filtrer par catégorie (optionnel)
            alpha: Poids pour la similarité (défaut: 0.6)
            beta: Poids pour MemoryRank (défaut: 0.4)
        
        Returns:
            Liste de dictionnaires contenant les souvenirs triés par score combiné
        """
        from .semantic_filter import SemanticFilter
        
        # Normaliser les poids
        total = alpha + beta
        if total > 0:
            alpha = alpha / total
            beta = beta / total
        
        # Segmenter la requête (utiliser première phrase si plusieurs)
        query_phrases = query.split('.')
        query_phrase = query_phrases[0].strip() if query_phrases else query.strip()
        
        if not query_phrase:
            return []
        
        session = self.db.get_session()
        try:
            # Récupérer tous les souvenirs (ou filtrés par catégorie)
            query_db = session.query(SouvenirModel).filter(
                SouvenirModel.ttl > datetime.now(UTC)
            )
            if category:
                query_db = query_db.filter(SouvenirModel.category == category)
            memories = query_db.all()
            
            if not memories:
                return []
            
            # Calculer scores pour chaque souvenir
            semantic_filter = SemanticFilter()
            scored_memories = []
            
            for memory in memories:
                # Similarité avec la requête (utiliser nouveauté inversée)
                # Plus la phrase est similaire, plus le score est élevé
                similarity = 1.0 - semantic_filter.calculate_novelty(
                    query_phrase,
                    [memory.content]
                )
                
                # MemoryRank
                memory_rank = float(memory.memory_rank_score or 0.0)
                
                # Score combiné
                combined_score = alpha * similarity + beta * memory_rank
                
                scored_memories.append({
                    'memory': memory,
                    'score': combined_score,
                    'similarity': similarity,
                    'memory_rank': memory_rank
                })
            
            # Trier par score
            scored_memories.sort(key=lambda x: x['score'], reverse=True)
            
            # Retourner les top résultats
            result = []
            for item in scored_memories[:limit]:
                mem_dict = self._memory_to_dict(item['memory'])
                mem_dict['search_score'] = item['score']
                mem_dict['search_similarity'] = item['similarity']
                result.append(mem_dict)
            
            return result
        finally:
            session.close()
    
    def _memory_to_dict(self, memory: SouvenirModel) -> Dict[str, Any]:
        """Convertit un SouvenirModel en dictionnaire."""
        return {
            "memory_id": memory.memory_id,
            "category": memory.category,
            "content": memory.content,
            "tags": memory.tags.split(",") if memory.tags else [],
            "importance_score": memory.importance_score,
            "recency_score": memory.recency_score,
            "emotion_score": memory.emotion_score,
            "memory_rank_score": getattr(memory, 'memory_rank_score', 0.0),
            "frequency": memory.frequency,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
            "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        }
    
    def _trait_to_dict(self, trait: TraitModel) -> Dict[str, Any]:
        """Convertit un TraitModel en dictionnaire."""
        return {
            "trait_id": trait.trait_id,
            "type": trait.type,
            "label": trait.label,
            "value": trait.value,
            "weight": trait.weight,
            "confidence": trait.confidence,
            "version": trait.version,
            "last_update": trait.last_update.isoformat() if trait.last_update else None,
        }

