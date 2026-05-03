"""Processeur principal pour MemoryRank V2 - Traitement par phrases.

Orchestre le pipeline complet :
1. Segmentation en phrases
2. Filtrage sémantique
3. Stockage des phrases importantes
4. Création des liens MemoryRank
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, UTC

from .phrase_segmenter import PhraseSegmenter, Phrase
from .semantic_filter import SemanticFilter, ImportanceScore
from .rl_scorer import RLScorer
from .phrase_linker import PhraseLinker
from .store import MemoryStore
from .memory_rank_engine import MemoryRankEngine

logger = logging.getLogger(__name__)


class PhraseMemoryProcessor:
    """Processeur principal pour le traitement de mémoire par phrases."""
    
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        alpha: float = 0.4,
        beta: float = 0.3,
        gamma: float = 0.3,
        threshold: float = 0.5,
        min_phrase_length: int = 10
    ):
        """
        Initialise le processeur de mémoire par phrases.
        
        Args:
            memory_store: Instance de MemoryStore (créée si None)
            alpha: Poids pour la nouveauté
            beta: Poids pour le lien RL
            gamma: Poids pour la centralité
            threshold: Seuil d'importance pour stocker
            min_phrase_length: Longueur minimale des phrases
        """
        self.store = memory_store if memory_store else MemoryStore(use_memory_rank=True)
        self.segmenter = PhraseSegmenter(min_length=min_phrase_length)
        self.filter = SemanticFilter(
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            threshold=threshold
        )
        self.rl_scorer = RLScorer()
        self.phrase_linker = PhraseLinker()
        self.rank_engine = MemoryRankEngine(db=self.store.db)
        
        logger.info(
            f"PhraseMemoryProcessor initialisé "
            f"(α={alpha}, β={beta}, γ={gamma}, θ={threshold})"
        )
    
    async def process_interaction(
        self,
        interaction: Dict[str, Any]
    ) -> List[str]:
        """
        Traite une interaction complète et stocke les phrases importantes.
        
        Pipeline :
        1. Segmentation en phrases
        2. Récupération des souvenirs existants
        3. Filtrage sémantique
        4. Stockage des phrases importantes
        5. Création des liens MemoryRank
        
        Args:
            interaction: Dictionnaire avec 'prompt', 'response', 'session_id', etc.
        
        Returns:
            Liste des IDs des phrases stockées
        """
        prompt = interaction.get("prompt", "")
        response = interaction.get("response", "")
        session_id = interaction.get("session_id", "default")
        
        logger.info(f"Traitement interaction (session: {session_id[:8]}...)")
        
        # Étape 1 : Segmentation
        logger.debug("Étape 1 : Segmentation en phrases...")
        phrases = self.segmenter.segment_interaction(prompt, response)
        
        if not phrases:
            logger.info("Aucune phrase à traiter")
            return []
        
        logger.info(f"  → {len(phrases)} phrases segmentées")
        
        # Étape 2 : Récupérer les souvenirs existants
        logger.debug("Étape 2 : Récupération des souvenirs existants...")
        existing_memories = self._get_existing_memories()
        logger.info(f"  → {len(existing_memories)} souvenirs existants")
        
        # Étape 3 : Filtrage sémantique avec scores RL et centralité
        logger.debug("Étape 3 : Filtrage sémantique...")
        phrase_texts = [p.text for p in phrases]
        
        # Calculer les scores RL pour chaque phrase
        rl_scores = {}
        for phrase_text in phrase_texts:
            rl_score = self.rl_scorer.calculate_rl_score(
                phrase_text,
                memory_store=self.store
            )
            rl_scores[phrase_text] = rl_score
        
        # Récupérer les centralités existantes (si disponibles)
        # Pour les nouvelles phrases, centralité = 0.0 initialement
        centralities = {}
        for phrase_text in phrase_texts:
            # Chercher si une phrase similaire existe déjà avec un MemoryRank
            # Pour l'instant, on utilise 0.0 (sera calculé après stockage)
            centralities[phrase_text] = 0.0
        
        phrases_to_store = self.filter.filter_phrases(
            phrase_texts,
            existing_memories,
            rl_scores=rl_scores,
            centralities=centralities
        )
        
        if not phrases_to_store:
            logger.info("Aucune phrase importante à stocker")
            return []
        
        logger.info(f"  → {len(phrases_to_store)} phrases à stocker")
        # Log détaillé des phrases sélectionnées pour mémorisation (avant stockage)
        try:
            for idx, (phrase_text, importance) in enumerate(phrases_to_store, 1):
                preview = phrase_text[:120] + "..." if len(phrase_text) > 120 else phrase_text
                # importance est un ImportanceScore (semantic_filter.ImportanceScore)
                score = getattr(importance, "combined", None)
                if score is not None:
                    logger.info(f"    {idx}. (I={score:.3f}) {preview}")
                else:
                    logger.info(f"    {idx}. {preview}")
        except Exception as e:
            logger.debug(f"Erreur lors du logging des phrases à stocker: {e}")
        
        # Étape 4 : Stockage
        logger.debug("Étape 4 : Stockage des phrases...")
        stored_ids = []
        for phrase_text, importance in phrases_to_store:
            memory_id = self._store_phrase(
                phrase_text=phrase_text,
                importance=importance,
                session_id=session_id,
                interaction=interaction
            )
            if memory_id:
                stored_ids.append(memory_id)
        
        logger.info(f"  → {len(stored_ids)} phrases stockées")
        
        # Étape 5 : Création des liens MemoryRank
        if len(stored_ids) > 1:
            logger.debug("Étape 5 : Création des liens MemoryRank...")
            stored_phrases = [phrase for phrase, _ in phrases_to_store]
            links_created = self.phrase_linker.create_links_for_interaction(
                stored_phrases,
                stored_ids,
                self.store
            )
            logger.info(f"  → {links_created} liens créés")
        
        # Recalculer les scores MemoryRank (inclut la centralité)
        if stored_ids:
            logger.debug("Recalcul des scores MemoryRank...")
            ranks = self.rank_engine.compute_and_update_ranks()
            
            # Mettre à jour les centralités pour les phrases stockées
            # (pour référence future, même si pas utilisé immédiatement)
            logger.debug(f"  → Scores MemoryRank calculés pour {len(ranks)} souvenirs")
        
        logger.info(
            f"✅ Traitement terminé: {len(stored_ids)} phrases stockées "
            f"sur {len(phrases)} analysées"
        )
        
        return stored_ids
    
    def _get_existing_memories(self) -> List[str]:
        """Récupère les contenus des souvenirs existants."""
        try:
            context = self.store.get_context(limit_memories=100)
            memories = context.get("memories", [])
            return [m.get("content", "") for m in memories if m.get("content")]
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération des souvenirs: {e}")
            return []
    
    def _store_phrase(
        self,
        phrase_text: str,
        importance: ImportanceScore,
        session_id: str,
        interaction: Dict[str, Any]
    ) -> Optional[str]:
        """
        Stocke une phrase comme souvenir.
        
        Args:
            phrase_text: Texte de la phrase
            importance: Score d'importance
            session_id: ID de session
            interaction: Interaction source
        
        Returns:
            ID du souvenir créé ou None
        """
        try:
            # Déterminer la catégorie
            category = self._categorize_phrase(phrase_text)
            
            # Créer des tags
            tags = self._extract_tags(phrase_text, interaction, session_id)
            
            # Stocker
            memory_id = self.store.add_memory(
                category=category,
                content=phrase_text,
                tags=tags,
                importance_score=importance.combined,
                ttl_days=self._calculate_ttl(importance.combined, category)
            )
            
            logger.debug(f"  ✓ Phrase stockée: {memory_id[:8]}... - '{phrase_text[:50]}...'")
            
            return memory_id
        except Exception as e:
            logger.error(f"Erreur lors du stockage de la phrase: {e}")
            return None
    
    def _categorize_phrase(self, phrase: str) -> str:
        """Catégorise une phrase."""
        phrase_lower = phrase.lower()
        
        # Préférences
        if any(word in phrase_lower for word in ["préfère", "prefer", "aime", "like", "déteste", "hate"]):
            return "preference"
        
        # Faits
        if any(word in phrase_lower for word in ["fait", "fact", "important", "souviens", "remember"]):
            return "fact"
        
        # Par défaut
        return "fact"
    
    def _extract_tags(
        self,
        phrase: str,
        interaction: Dict[str, Any],
        session_id: str
    ) -> List[str]:
        """Extrait des tags pour une phrase."""
        tags = []
        
        # Tag de session
        tags.append(f"session:{session_id[:8]}")
        
        # Tags basés sur le contenu
        phrase_lower = phrase.lower()
        if "python" in phrase_lower:
            tags.append("python")
        if "ia" in phrase_lower or "ai" in phrase_lower:
            tags.append("ai")
        if "projet" in phrase_lower or "project" in phrase_lower:
            tags.append("project")
        
        return tags
    
    def _calculate_ttl(self, importance: float, category: str) -> int:
        """Calcule la durée de vie d'un souvenir."""
        base_ttl = {
            "preference": 90,
            "fact": 60,
            "alert": 7,
            "context": 30
        }.get(category, 30)
        
        # Ajuster selon l'importance
        if importance >= 0.8:
            return int(base_ttl * 1.5)
        elif importance >= 0.6:
            return base_ttl
        else:
            return int(base_ttl * 0.7)
    

