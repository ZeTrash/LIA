"""Segmentation de texte en phrases sémantiques pour MemoryRank V2.

Ce module décompose les prompts/interactions en phrases individuelles,
permettant un stockage et une analyse plus granulaires.
"""

import re
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Phrase:
    """Représente une phrase segmentée."""
    text: str
    start_pos: int
    end_pos: int
    is_question: bool = False
    is_exclamation: bool = False


class PhraseSegmenter:
    """Segmente un texte en phrases sémantiques cohérentes."""
    
    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 500,
        filter_non_informative: bool = True
    ):
        """
        Initialise le segmenteur de phrases.
        
        Args:
            min_length: Longueur minimale d'une phrase (caractères)
            max_length: Longueur maximale d'une phrase (caractères)
            filter_non_informative: Filtrer les phrases non informatives
        """
        self.min_length = min_length
        self.max_length = max_length
        self.filter_non_informative = filter_non_informative
        
        # Phrases non informatives à filtrer
        self.non_informative_patterns = [
            r'^\s*(ok|d\'accord|daccord|oui|non|merci|thanks?|thank you)\s*[.!?]?\s*$',
            r'^\s*(salut|hello|hi|hey)\s*[.!?]?\s*$',
            r'^\s*(à bientôt|bye|goodbye|au revoir)\s*[.!?]?\s*$',
            r'^\s*(\.\.\.|…)\s*$',
            r'^\s*$',
        ]
        
        logger.info(f"PhraseSegmenter initialisé (min={min_length}, max={max_length})")
    
    def segment(self, text: str) -> List[Phrase]:
        """
        Segmente un texte en phrases.
        
        Args:
            text: Texte à segmenter
        
        Returns:
            Liste de phrases segmentées
        """
        if not text or not text.strip():
            return []
        
        # Normaliser le texte
        normalized_text = self._normalize_text(text)
        
        # Détecter les limites de phrases
        phrases = self._detect_sentence_boundaries(normalized_text)
        
        # Filtrer les phrases
        filtered_phrases = self._filter_phrases(phrases)
        
        logger.debug(f"Segmentation: {len(phrases)} phrases détectées, {len(filtered_phrases)} après filtrage")
        
        return filtered_phrases
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalise le texte avant segmentation.
        
        - Remplace les espaces multiples par un seul espace
        - Normalise la ponctuation
        - Gère les cas spéciaux
        - Corrige les abréviations courantes pour éviter les fausses coupures
        """
        # Remplacer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Normaliser les points de suspension
        text = re.sub(r'\.{3,}', '...', text)
        
        # Protéger les abréviations courantes (M., Mme, Dr., etc.)
        # Pour éviter qu'elles soient considérées comme fins de phrases
        abbreviations = ['M\\.', 'Mme', 'Mlle', 'Dr\\.', 'Prof\\.', 'M\\.', 'J\\.']
        for abbr in abbreviations:
            text = re.sub(f'({abbr})\\s+', r'\1 ', text)
        
        # S'assurer qu'il y a un espace après la ponctuation si nécessaire
        # Mais pas après les abréviations
        text = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', text)
        
        return text.strip()
    
    def _detect_sentence_boundaries(self, text: str) -> List[Phrase]:
        """
        Détecte les limites des phrases dans le texte.
        
        Utilise une approche basée sur regex pour détecter :
        - Points suivis d'un espace et d'une majuscule
        - Points d'exclamation
        - Points d'interrogation
        - Points de suspension
        """
        phrases = []
        
        # Pattern amélioré : cherche ponctuation suivie d'espace et majuscule (au moins 2 caractères)
        # ou ponctuation en fin de texte
        # Exclut les cas où une seule lettre majuscule suit (comme "J" seul)
        pattern = r'([.!?]+)\s+([A-Z][a-zA-Z]{1,})|([.!?]+)$'
        
        # Trouver toutes les positions de fin de phrase
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            # Si aucune ponctuation trouvée, considérer tout le texte comme une phrase
            if len(text.strip()) >= self.min_length:
                phrases.append(Phrase(
                    text=text.strip(),
                    start_pos=0,
                    end_pos=len(text),
                    is_question='?' in text,
                    is_exclamation='!' in text
                ))
            return phrases
        
        # Construire les phrases à partir des matches
        start = 0
        for i, match in enumerate(matches):
            # Déterminer la fin de la phrase
            if match.group(2):  # Majuscule trouvée après ponctuation
                # La phrase se termine juste avant l'espace qui précède la majuscule
                end = match.start() + len(match.group(1))
            else:  # Fin de texte
                end = match.end()
            
            # Extraire la phrase
            phrase_text = text[start:end].strip()
            
            # Nettoyer la ponctuation finale
            phrase_text = re.sub(r'[.!?]+$', '', phrase_text).strip()
            
            # Vérifier la longueur minimale avant d'ajouter
            if phrase_text and len(phrase_text) >= self.min_length:
                phrases.append(Phrase(
                    text=phrase_text,
                    start_pos=start,
                    end_pos=end,
                    is_question='?' in (match.group(1) or match.group(3) or ''),
                    is_exclamation='!' in (match.group(1) or match.group(3) or '')
                ))
            
            # Déplacer le début pour la prochaine phrase
            if match.group(2):  # Si on a trouvé une majuscule après
                # Commencer après l'espace (la majuscule fait partie de la prochaine phrase)
                start = match.start() + len(match.group(1)) + 1
            else:  # Fin de texte
                start = end
        
        # Ajouter la dernière phrase si elle n'a pas été capturée
        if start < len(text):
            remaining = text[start:].strip()
            # Nettoyer la ponctuation finale
            remaining = re.sub(r'[.!?]+$', '', remaining).strip()
            if remaining and len(remaining) >= self.min_length:
                phrases.append(Phrase(
                    text=remaining,
                    start_pos=start,
                    end_pos=len(text),
                    is_question='?' in text[start:],
                    is_exclamation='!' in text[start:]
                ))
        
        return phrases
    
    def _filter_phrases(self, phrases: List[Phrase]) -> List[Phrase]:
        """
        Filtre les phrases selon les critères de qualité.
        
        - Longueur minimale/maximale
        - Phrases non informatives
        """
        filtered = []
        
        for phrase in phrases:
            # Vérifier la longueur
            if len(phrase.text) < self.min_length:
                logger.debug(f"Phrase filtrée (trop courte): '{phrase.text[:50]}...'")
                continue
            
            if len(phrase.text) > self.max_length:
                logger.debug(f"Phrase filtrée (trop longue): '{phrase.text[:50]}...'")
                continue
            
            # Filtrer les phrases non informatives
            if self.filter_non_informative:
                if self._is_non_informative(phrase.text):
                    logger.debug(f"Phrase filtrée (non informative): '{phrase.text[:50]}...'")
                    continue
            
            filtered.append(phrase)
        
        return filtered
    
    def _is_non_informative(self, text: str) -> bool:
        """
        Vérifie si une phrase est non informative.
        
        Returns:
            True si la phrase doit être filtrée
        """
        text_lower = text.lower().strip()
        
        # Vérifier les patterns non informatifs
        for pattern in self.non_informative_patterns:
            if re.match(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Vérifier si la phrase ne contient que de la ponctuation
        if re.match(r'^[^\w\s]+$', text):
            return True
        
        return False
    
    def segment_interaction(self, prompt: str, response: Optional[str] = None) -> List[Phrase]:
        """
        Segmente une interaction complète (prompt + réponse optionnelle).
        
        Args:
            prompt: Prompt de l'utilisateur
            response: Réponse générée (optionnel)
        
        Returns:
            Liste de toutes les phrases de l'interaction
        """
        all_phrases = []
        
        # Segmenter le prompt
        prompt_phrases = self.segment(prompt)
        all_phrases.extend(prompt_phrases)
        
        # Segmenter la réponse si fournie
        if response:
            response_phrases = self.segment(response)
            all_phrases.extend(response_phrases)
        
        logger.info(f"Interaction segmentée: {len(prompt_phrases)} phrases du prompt, "
                   f"{len(response_phrases) if response else 0} phrases de la réponse")
        
        return all_phrases

