"""Création automatique de liens entre phrases pour MemoryRank V2.

Ce module crée différents types de liens entre phrases :
- Co-occurrence (phrases dans la même interaction)
- Dépendance causale (patterns linguistiques)
- Similarité sémantique (embeddings)
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class PhraseLinker:
    """Crée des liens entre phrases pour le graphe MemoryRank."""
    
    def __init__(
        self,
        similarity_threshold: float = 0.7,
        enable_causal_detection: bool = True,
        enable_similarity_detection: bool = True
    ):
        """
        Initialise le créateur de liens.
        
        Args:
            similarity_threshold: Seuil de similarité pour créer un lien (0.0-1.0)
            enable_causal_detection: Activer la détection de dépendances causales
            enable_similarity_detection: Activer la détection de similarité sémantique
        """
        self.similarity_threshold = similarity_threshold
        self.enable_causal_detection = enable_causal_detection
        self.enable_similarity_detection = enable_similarity_detection
        
        # Patterns pour détecter les dépendances causales
        self.causal_patterns = [
            (r'(.+?)\s+(?:parce que|car|caractérisé par)\s+(.+)', 'because'),
            (r'(.+?)\s+(?:donc|ainsi|par conséquent)\s+(.+)', 'therefore'),
            (r'(.+?)\s+(?:si|quand|lorsque)\s+(.+?)\s+(?:alors|donc)\s+(.+)', 'if_then'),
            (r'(.+?)\s+(?:cause|provoque|entraîne)\s+(.+)', 'causes'),
            (r'(.+?)\s+(?:résulte de|découle de|provient de)\s+(.+)', 'results_from'),
        ]
        
        logger.info(
            f"PhraseLinker initialisé "
            f"(similarity_threshold={similarity_threshold}, "
            f"causal={enable_causal_detection}, similarity={enable_similarity_detection})"
        )
    
    def create_links_for_interaction(
        self,
        phrases: List[str],
        memory_ids: List[str],
        memory_store
    ) -> int:
        """
        Crée des liens pour toutes les phrases d'une interaction.
        
        Args:
            phrases: Liste des phrases de l'interaction
            memory_ids: Liste des IDs des souvenirs correspondants
            memory_store: MemoryStore pour créer les liens
        
        Returns:
            Nombre de liens créés
        """
        if len(phrases) != len(memory_ids):
            logger.warning(f"Nombre de phrases ({len(phrases)}) != nombre de IDs ({len(memory_ids)})")
            return 0
        
        links_created = 0
        
        # 1. Liens de co-occurrence (toutes les phrases de la même interaction)
        links_created += self._create_cooccurrence_links(memory_ids, memory_store)
        
        # 2. Liens de dépendance causale
        if self.enable_causal_detection:
            links_created += self._create_causal_links(phrases, memory_ids, memory_store)
        
        # 3. Liens de similarité sémantique
        if self.enable_similarity_detection:
            links_created += self._create_similarity_links(phrases, memory_ids, memory_store)
        
        logger.info(f"Liens créés pour interaction: {links_created} liens")
        
        return links_created
    
    def _create_cooccurrence_links(
        self,
        memory_ids: List[str],
        memory_store
    ) -> int:
        """Crée des liens de co-occurrence entre toutes les phrases."""
        links_created = 0
        
        for i, mem_id_1 in enumerate(memory_ids):
            for mem_id_2 in memory_ids[i+1:]:
                try:
                    link_id = memory_store.add_memory_link(
                        source_memory_id=mem_id_1,
                        target_memory_id=mem_id_2,
                        weight=1.0,
                        link_type="cooccurrence",
                        metadata={"source": "phrase_linker", "type": "cooccurrence"}
                    )
                    if link_id:
                        links_created += 1
                except Exception as e:
                    logger.debug(f"Erreur création lien co-occurrence: {e}")
        
        return links_created
    
    def _create_causal_links(
        self,
        phrases: List[str],
        memory_ids: List[str],
        memory_store
    ) -> int:
        """Crée des liens de dépendance causale."""
        links_created = 0
        
        for i, phrase in enumerate(phrases):
            for pattern, link_type in self.causal_patterns:
                matches = re.finditer(pattern, phrase, re.IGNORECASE)
                for match in matches:
                    # Extraire les parties causales
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Chercher si d'autres phrases correspondent aux parties causales
                        for j, other_phrase in enumerate(phrases):
                            if i != j:
                                # Vérifier si la phrase correspond à une partie causale
                                if self._phrase_matches_causal_part(other_phrase, groups):
                                    try:
                                        # Créer un lien causal
                                        link_id = memory_store.add_memory_link(
                                            source_memory_id=memory_ids[i],
                                            target_memory_id=memory_ids[j],
                                            weight=1.5,  # Poids plus élevé pour les liens causaux
                                            link_type="causal",
                                            metadata={
                                                "source": "phrase_linker",
                                                "type": "causal",
                                                "pattern": link_type
                                            }
                                        )
                                        if link_id:
                                            links_created += 1
                                    except Exception as e:
                                        logger.debug(f"Erreur création lien causal: {e}")
        
        return links_created
    
    def _phrase_matches_causal_part(self, phrase: str, causal_groups: Tuple) -> bool:
        """Vérifie si une phrase correspond à une partie causale."""
        phrase_lower = phrase.lower()
        
        for group in causal_groups:
            if group and len(group) > 5:  # Ignorer les groupes trop courts
                group_lower = group.lower().strip()
                # Vérifier si la phrase contient des mots clés de la partie causale
                group_words = set(re.findall(r'\b\w+\b', group_lower))
                phrase_words = set(re.findall(r'\b\w+\b', phrase_lower))
                
                # Si au moins 30% des mots correspondent
                if group_words and phrase_words:
                    overlap = len(group_words & phrase_words) / len(group_words)
                    if overlap > 0.3:
                        return True
        
        return False
    
    def _create_similarity_links(
        self,
        phrases: List[str],
        memory_ids: List[str],
        memory_store
    ) -> int:
        """Crée des liens de similarité sémantique."""
        links_created = 0
        
        # Calculer la similarité entre toutes les paires de phrases
        for i, phrase1 in enumerate(phrases):
            for j, phrase2 in enumerate(phrases[i+1:], start=i+1):
                similarity = self._calculate_similarity(phrase1, phrase2)
                
                if similarity >= self.similarity_threshold:
                    try:
                        link_id = memory_store.add_memory_link(
                            source_memory_id=memory_ids[i],
                            target_memory_id=memory_ids[j],
                            weight=similarity,  # Poids basé sur la similarité
                            link_type="similarity",
                            metadata={
                                "source": "phrase_linker",
                                "type": "similarity",
                                "similarity_score": similarity
                            }
                        )
                        if link_id:
                            links_created += 1
                    except Exception as e:
                        logger.debug(f"Erreur création lien similarité: {e}")
        
        return links_created
    
    def _calculate_similarity(self, phrase1: str, phrase2: str) -> float:
        """
        Calcule la similarité sémantique entre deux phrases.
        
        Pour l'instant, utilise une approche basée sur les mots communs.
        Peut être améliorée avec des embeddings (sentence-transformers).
        
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
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'à', 'a', 'est', 'sont'}
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        return words

