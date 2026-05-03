"""Calcul du score RL pour les phrases dans MemoryRank V2.

Ce module calcule l'utilité d'une phrase pour l'apprentissage par renforcement
en analysant l'historique des récompenses associées à des phrases similaires.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, UTC, timedelta

logger = logging.getLogger(__name__)


class RLScorer:
    """Calcule les scores RL pour les phrases."""
    
    def __init__(
        self,
        lookback_days: int = 30,
        decay_factor: float = 0.9
    ):
        """
        Initialise le calculateur de scores RL.
        
        Args:
            lookback_days: Nombre de jours à regarder en arrière pour l'historique
            decay_factor: Facteur de décroissance pour les récompenses anciennes
        """
        self.lookback_days = lookback_days
        self.decay_factor = decay_factor
        
        logger.info(f"RLScorer initialisé (lookback={lookback_days}j, decay={decay_factor})")
    
    def calculate_rl_score(
        self,
        phrase: str,
        rl_history: Optional[List[Dict]] = None,
        memory_store=None
    ) -> float:
        """
        Calcule le score RL d'une phrase.
        
        Args:
            phrase: Phrase à évaluer
            rl_history: Historique RL explicite (optionnel)
            memory_store: MemoryStore pour récupérer l'historique (optionnel)
        
        Returns:
            Score RL entre 0.0 et 1.0
        """
        # Si pas d'historique fourni, essayer de le récupérer depuis memory_store
        if rl_history is None and memory_store:
            rl_history = self._get_rl_history_from_store(memory_store)
        
        if not rl_history:
            # Pas d'historique disponible, retourner score neutre
            return 0.5
        
        # Chercher des phrases similaires dans l'historique RL
        similar_phrases = self._find_similar_phrases(phrase, rl_history)
        
        if not similar_phrases:
            # Aucune phrase similaire trouvée, score neutre
            return 0.5
        
        # Calculer la moyenne pondérée des récompenses
        total_weighted_reward = 0.0
        total_weight = 0.0
        
        now = datetime.now(UTC)
        
        for item in similar_phrases:
            reward = item.get('reward', 0.0)
            similarity = item.get('similarity', 0.0)
            occurred_at = item.get('occurred_at')
            
            # Calculer le poids temporel (décroissance exponentielle)
            if occurred_at:
                if isinstance(occurred_at, str):
                    # Parser la date si c'est une string
                    try:
                        occurred_at = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
                    except:
                        occurred_at = None
                
                if occurred_at:
                    if occurred_at.tzinfo is None:
                        occurred_at = occurred_at.replace(tzinfo=UTC)
                    
                    age_days = (now - occurred_at).total_seconds() / 86400.0
                    temporal_weight = self.decay_factor ** age_days
                else:
                    temporal_weight = 1.0
            else:
                temporal_weight = 1.0
            
            # Poids combiné : similarité * poids temporel
            weight = similarity * temporal_weight
            
            total_weighted_reward += reward * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        # Score RL normalisé entre 0.0 et 1.0
        rl_score = total_weighted_reward / total_weight
        
        # Normaliser pour être entre 0.0 et 1.0
        # (les récompenses peuvent être négatives ou > 1.0)
        rl_score = max(0.0, min(1.0, (rl_score + 1.0) / 2.0))
        
        logger.debug(f"Score RL pour '{phrase[:50]}...': {rl_score:.3f} "
                    f"({len(similar_phrases)} phrases similaires)")
        
        return rl_score
    
    def _find_similar_phrases(
        self,
        phrase: str,
        rl_history: List[Dict],
        similarity_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Trouve des phrases similaires dans l'historique RL.
        
        Args:
            phrase: Phrase à comparer
            rl_history: Historique RL
            similarity_threshold: Seuil de similarité minimum
        
        Returns:
            Liste des items similaires avec leur similarité
        """
        similar_items = []
        
        for item in rl_history:
            history_phrase = item.get('phrase') or item.get('content', '')
            if not history_phrase:
                continue
            
            # Calculer la similarité
            similarity = self._phrase_similarity(phrase, history_phrase)
            
            if similarity >= similarity_threshold:
                item_with_similarity = item.copy()
                item_with_similarity['similarity'] = similarity
                similar_items.append(item_with_similarity)
        
        # Trier par similarité décroissante
        similar_items.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
        
        return similar_items
    
    def _phrase_similarity(self, phrase1: str, phrase2: str) -> float:
        """
        Calcule la similarité entre deux phrases.
        
        Utilise une approche simple basée sur les mots communs.
        Peut être améliorée avec des embeddings.
        
        Returns:
            Similarité entre 0.0 et 1.0
        """
        # Normaliser les phrases
        words1 = set(self._extract_words(phrase1.lower()))
        words2 = set(self._extract_words(phrase2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return 0.0
        
        jaccard = len(intersection) / len(union)
        
        # Ajuster pour la longueur similaire
        length_ratio = min(len(words1), len(words2)) / max(len(words1), len(words2))
        
        # Combinaison pondérée
        similarity = 0.7 * jaccard + 0.3 * length_ratio
        
        return min(1.0, similarity)
    
    def _extract_words(self, text: str) -> List[str]:
        """Extrait les mots significatifs d'un texte."""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'à', 'a', 'est', 'sont'}
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        return words
    
    def _get_rl_history_from_store(self, memory_store) -> List[Dict]:
        """
        Récupère l'historique RL depuis le MemoryStore.
        
        Pour l'instant, retourne une liste vide car l'historique RL
        n'est pas encore stocké dans la base de données.
        Peut être étendu pour récupérer depuis InteractionModel avec scores.
        """
        # TODO: Implémenter la récupération depuis la base de données
        # Pour l'instant, retourner liste vide
        return []
    
    def update_rl_history(
        self,
        phrase: str,
        reward: float,
        occurred_at: Optional[datetime] = None,
        memory_store=None
    ):
        """
        Met à jour l'historique RL avec une nouvelle récompense.
        
        Args:
            phrase: Phrase associée à la récompense
            reward: Valeur de la récompense (-1.0 à 1.0)
            occurred_at: Date de l'événement (défaut: maintenant)
            memory_store: MemoryStore pour persister (optionnel)
        """
        if occurred_at is None:
            occurred_at = datetime.now(UTC)
        
        # Pour l'instant, on ne persiste pas l'historique RL
        # Cela peut être ajouté plus tard avec une table dédiée
        
        logger.debug(f"Historique RL mis à jour: phrase='{phrase[:50]}...', reward={reward:.3f}")
        
        # Si memory_store fourni, on pourrait stocker dans InteractionModel avec scores
        if memory_store:
            # TODO: Stocker dans InteractionModel avec le score de récompense
            pass

