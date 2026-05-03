"""Filtrage sémantique pour MemoryRank V2.

Calcule l'importance d'une phrase en combinant :
- Nouveauté (vs souvenirs existants)
- Lien RL (utilité pour l'apprentissage)
- Centralité MemoryRank (importance structurelle)
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class ImportanceScore:
    """Score d'importance décomposé pour une phrase."""
    novelty: float  # 0.0 = redondant, 1.0 = complètement nouveau
    rl_score: float  # 0.0 = inutile, 1.0 = très utile pour RL
    centrality: float  # 0.0 = périphérique, 1.0 = très central
    combined: float  # Score combiné selon les poids


class SemanticFilter:
    """Filtre sémantique pour déterminer l'importance des phrases."""
    
    def __init__(
        self,
        alpha: float = 0.4,
        beta: float = 0.3,
        gamma: float = 0.3,
        threshold: float = 0.5,
        novelty_threshold: float = 0.3
    ):
        """
        Initialise le filtre sémantique.
        
        Args:
            alpha: Poids pour la nouveauté (défaut: 0.4)
            beta: Poids pour le lien RL (défaut: 0.3)
            gamma: Poids pour la centralité (défaut: 0.3)
            threshold: Seuil d'importance pour stocker (défaut: 0.5)
            novelty_threshold: Seuil de similarité pour considérer comme nouveau (défaut: 0.3)
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.threshold = threshold
        self.novelty_threshold = novelty_threshold
        
        # Normaliser les poids pour qu'ils somment à 1.0
        total = alpha + beta + gamma
        if total > 0:
            self.alpha = alpha / total
            self.beta = beta / total
            self.gamma = gamma / total
        
        logger.info(f"SemanticFilter initialisé (α={self.alpha:.2f}, β={self.beta:.2f}, γ={self.gamma:.2f}, θ={threshold})")
    
    def calculate_novelty(
        self,
        phrase: str,
        existing_memories: List[str]
    ) -> float:
        """
        Calcule la nouveauté d'une phrase par rapport aux souvenirs existants.
        
        Args:
            phrase: Phrase à évaluer
            existing_memories: Liste des contenus de souvenirs existants
        
        Returns:
            Score de nouveauté entre 0.0 (redondant) et 1.0 (complètement nouveau)
        """
        if not existing_memories:
            # Si aucun souvenir existant, la phrase est complètement nouvelle
            return 1.0
        
        # Calculer la similarité maximale avec les souvenirs existants
        max_similarity = 0.0
        
        for memory in existing_memories:
            similarity = self._text_similarity(phrase, memory)
            max_similarity = max(max_similarity, similarity)
        
        # Nouveauté = 1 - similarité maximale
        novelty = 1.0 - max_similarity
        
        logger.debug(f"Nouveauté de '{phrase[:50]}...': {novelty:.3f} (similarité max: {max_similarity:.3f})")
        
        return novelty
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité entre deux textes (approche améliorée basée sur mots communs).
        
        Utilise une approche améliorée avec :
        - Jaccard similarity sur les mots
        - Poids pour les mots importants (longs, non-stopwords)
        - Similarité de séquence (ordre des mots)
        
        Peut être améliorée avec des embeddings (sentence-transformers) plus tard.
        
        Returns:
            Similarité entre 0.0 et 1.0
        """
        # Normaliser les textes
        words1 = self._extract_words(text1.lower())
        words2 = self._extract_words(text2.lower())
        
        if not words1 or not words2:
            return 0.0
        
        # Convertir en sets pour Jaccard
        set1 = set(words1)
        set2 = set(words2)
        
        # Jaccard similarity de base
        intersection = set1 & set2
        union = set1 | set2
        
        if not union:
            return 0.0
        
        jaccard = len(intersection) / len(union)
        
        # Similarité pondérée par l'importance des mots
        # Les mots plus longs et moins communs ont plus de poids
        total_weight = 0.0
        intersection_weight = 0.0
        
        # Calculer les poids pour chaque mot
        word_weights = {}
        all_words = set1 | set2
        
        for word in all_words:
            # Poids basé sur la longueur (mots plus longs = plus importants)
            length_weight = len(word) / 10.0  # Normaliser sur longueur max ~10
            # Poids basé sur la fréquence (mots uniques = plus importants)
            freq_in_1 = words1.count(word)
            freq_in_2 = words2.count(word)
            freq_weight = 1.0 / (1.0 + freq_in_1 + freq_in_2)
            word_weights[word] = length_weight * freq_weight
        
        # Calculer la similarité pondérée
        for word in intersection:
            intersection_weight += word_weights.get(word, 1.0)
        
        for word in union:
            total_weight += word_weights.get(word, 1.0)
        
        weighted_similarity = intersection_weight / total_weight if total_weight > 0 else 0.0
        
        # Similarité de séquence (ordre des mots communs)
        # Trouver la plus longue sous-séquence commune
        common_words_1 = [w for w in words1 if w in set2]
        common_words_2 = [w for w in words2 if w in set1]
        
        sequence_similarity = 0.0
        if common_words_1 and common_words_2:
            # Calculer la similarité de séquence simple
            matches = sum(1 for i, w in enumerate(common_words_1[:len(common_words_2)]) 
                         if i < len(common_words_2) and w == common_words_2[i])
            sequence_similarity = matches / max(len(common_words_1), len(common_words_2))
        
        # Ratio de longueur
        length_ratio = min(len(words1), len(words2)) / max(len(words1), len(words2))
        
        # Combinaison pondérée : Jaccard (40%) + Pondéré (40%) + Séquence (10%) + Longueur (10%)
        similarity = (
            0.4 * jaccard +
            0.4 * weighted_similarity +
            0.1 * sequence_similarity +
            0.1 * length_ratio
        )
        
        return min(1.0, max(0.0, similarity))
    
    def _extract_words(self, text: str) -> List[str]:
        """Extrait les mots significatifs d'un texte."""
        # Supprimer la ponctuation et extraire les mots
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrer les mots trop courts (stop words basiques)
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'à', 'a', 'est', 'sont'}
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return words
    
    def calculate_importance(
        self,
        phrase: str,
        novelty: float,
        rl_score: float = 0.5,
        centrality: float = 0.0
    ) -> ImportanceScore:
        """
        Calcule le score d'importance combiné d'une phrase.
        
        Args:
            phrase: Phrase à évaluer
            novelty: Score de nouveauté (0.0-1.0)
            rl_score: Score RL (0.0-1.0, défaut: 0.5 = neutre)
            centrality: Score de centralité MemoryRank (0.0-1.0, défaut: 0.0)
        
        Returns:
            ImportanceScore avec tous les composants
        """
        # Score combiné
        combined = (
            self.alpha * novelty +
            self.beta * rl_score +
            self.gamma * centrality
        )
        
        score = ImportanceScore(
            novelty=novelty,
            rl_score=rl_score,
            centrality=centrality,
            combined=combined
        )
        
        logger.debug(
            f"Importance de '{phrase[:50]}...': "
            f"nouveauté={novelty:.3f}, RL={rl_score:.3f}, centralité={centrality:.3f}, "
            f"combiné={combined:.3f}"
        )
        
        return score
    
    def should_store(
        self,
        phrase: str,
        existing_memories: List[str],
        rl_score: Optional[float] = None,
        centrality: Optional[float] = None
    ) -> Tuple[bool, ImportanceScore]:
        """
        Détermine si une phrase doit être stockée.
        
        Args:
            phrase: Phrase à évaluer
            existing_memories: Liste des souvenirs existants
            rl_score: Score RL (optionnel, défaut: 0.5)
            centrality: Score de centralité (optionnel, défaut: 0.0)
        
        Returns:
            Tuple (should_store, ImportanceScore)
        """
        # Calculer la nouveauté
        novelty = self.calculate_novelty(phrase, existing_memories)
        
        # Utiliser les valeurs par défaut si non fournies
        if rl_score is None:
            rl_score = 0.5  # Score neutre
        if centrality is None:
            centrality = 0.0  # Pas encore de centralité calculée
        
        # Calculer l'importance
        importance = self.calculate_importance(phrase, novelty, rl_score, centrality)
        
        # Décision
        should_store = importance.combined > self.threshold
        
        if should_store:
            logger.info(
                f"✅ Phrase à stocker: '{phrase[:50]}...' "
                f"(importance={importance.combined:.3f} > {self.threshold})"
            )
        else:
            logger.debug(
                f"❌ Phrase non stockée: '{phrase[:50]}...' "
                f"(importance={importance.combined:.3f} <= {self.threshold})"
            )
        
        return should_store, importance
    
    def filter_phrases(
        self,
        phrases: List[str],
        existing_memories: List[str],
        rl_scores: Optional[Dict[str, float]] = None,
        centralities: Optional[Dict[str, float]] = None
    ) -> List[Tuple[str, ImportanceScore]]:
        """
        Filtre une liste de phrases et retourne celles à stocker.
        
        Args:
            phrases: Liste des phrases à filtrer
            existing_memories: Liste des souvenirs existants
            rl_scores: Dictionnaire {phrase: rl_score} (optionnel)
            centralities: Dictionnaire {phrase: centrality} (optionnel)
        
        Returns:
            Liste de tuples (phrase, ImportanceScore) pour les phrases à stocker
        """
        phrases_to_store = []
        
        for phrase in phrases:
            rl_score = rl_scores.get(phrase, 0.5) if rl_scores else 0.5
            centrality = centralities.get(phrase, 0.0) if centralities else 0.0
            
            should_store, importance = self.should_store(
                phrase, existing_memories, rl_score, centrality
            )
            
            if should_store:
                phrases_to_store.append((phrase, importance))
        
        logger.info(
            f"Filtrage: {len(phrases)} phrases analysées, "
            f"{len(phrases_to_store)} à stocker"
        )
        
        return phrases_to_store

