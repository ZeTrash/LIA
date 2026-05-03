"""Module de scoring de qualité des réponses pour évaluer la cohérence et la pertinence."""

import re
import logging
from typing import Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class QualityScorer:
    """Évalue la qualité d'une réponse selon plusieurs critères."""
    
    # Patterns de refus génériques
    REFUSAL_PATTERNS = [
        r"je ne peux pas",
        r"je ne peux pas reproduire",
        r"je ne peux pas critiquer",
        r"désolé.*je ne peux pas",
        r"je ne suis pas.*capable",
        r"je ne peux pas vous aider",
        r"je ne peux pas fournir",
        r"je ne peux pas répondre",
        r"je ne peux pas commenter",
        r"je ne peux pas discuter",
        r"je ne peux pas analyser",
        r"je ne peux pas traiter",
    ]
    
    def __init__(self):
        """Initialise le scorer de qualité."""
        pass
    
    def score_response(
        self,
        response: str,
        question: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Score une réponse selon plusieurs critères.
        
        Args:
            response: La réponse à évaluer
            question: La question posée (optionnel, pour cohérence)
            context: Contexte additionnel (optionnel)
        
        Returns:
            Dictionnaire avec scores et métadonnées
        """
        if not response or len(response.strip()) < 10:
            return {
                "total_score": 0.0,
                "coherence": 0.0,
                "lexical_diversity": 0.0,
                "no_refusal": 0.0,
                "length_score": 0.0,
                "is_valid": False,
                "issues": ["Réponse trop courte"]
            }
        
        # Scores individuels
        coherence_score = self._score_coherence(response, question, context)
        diversity_score = self._score_lexical_diversity(response)
        no_refusal_score = self._score_no_refusal(response)
        length_score = self._score_length(response)
        
        # Score total (pondéré)
        total_score = (
            coherence_score * 0.35 +
            diversity_score * 0.25 +
            no_refusal_score * 0.25 +
            length_score * 0.15
        )
        
        # Identifier les problèmes
        issues = []
        if coherence_score < 0.5:
            issues.append("Cohérence faible avec la question")
        if diversity_score < 0.4:
            issues.append("Diversité lexicale faible")
        if no_refusal_score < 0.8:
            issues.append("Contient des refus génériques")
        if length_score < 0.3:
            issues.append("Réponse trop courte")
        
        return {
            "total_score": round(total_score, 3),
            "coherence": round(coherence_score, 3),
            "lexical_diversity": round(diversity_score, 3),
            "no_refusal": round(no_refusal_score, 3),
            "length_score": round(length_score, 3),
            "is_valid": total_score >= 0.6 and no_refusal_score >= 0.7,
            "issues": issues,
            "response_length": len(response)
        }
    
    def _score_coherence(
        self,
        response: str,
        question: Optional[str] = None,
        context: Optional[str] = None
    ) -> float:
        """
        Score de cohérence avec la question.
        
        Si question fournie: vérifie la présence de mots-clés pertinents.
        Sinon: score basé sur la structure de la réponse.
        """
        if not question:
            # Score basé sur la structure (présence de connecteurs logiques)
            logical_connectors = [
                "car", "parce que", "donc", "ainsi", "en effet",
                "cependant", "toutefois", "néanmoins", "mais",
                "de plus", "en outre", "par ailleurs",
                "premièrement", "deuxièmement", "en conclusion"
            ]
            found_connectors = sum(1 for conn in logical_connectors if conn.lower() in response.lower())
            return min(0.7 + (found_connectors * 0.05), 1.0)
        
        # Extraire mots-clés de la question (mots significatifs)
        question_words = set(re.findall(r'\b\w{4,}\b', question.lower()))
        # Enlever mots vides
        stop_words = {"cette", "cette", "quels", "quelles", "comment", "pourquoi", "quand", "où", "comment"}
        question_words = {w for w in question_words if w not in stop_words}
        
        if not question_words:
            return 0.5
        
        # Vérifier présence dans la réponse
        response_lower = response.lower()
        found_words = sum(1 for word in question_words if word in response_lower)
        coverage = found_words / len(question_words)
        
        return min(coverage * 1.2, 1.0)  # Bonus si tous les mots trouvés
    
    def _score_lexical_diversity(self, response: str) -> float:
        """
        Score de diversité lexicale (ratio unique/total mots).
        
        Plus la diversité est élevée, plus la réponse est riche.
        """
        words = re.findall(r'\b\w+\b', response.lower())
        if not words:
            return 0.0
        
        unique_words = set(words)
        diversity_ratio = len(unique_words) / len(words)
        
        # Normaliser (bonne diversité = 0.6-0.8)
        if diversity_ratio < 0.3:
            return diversity_ratio * 1.5
        elif diversity_ratio < 0.6:
            return 0.5 + (diversity_ratio - 0.3) * 0.5
        else:
            return min(0.8 + (diversity_ratio - 0.6) * 0.5, 1.0)
    
    def _score_no_refusal(self, response: str) -> float:
        """
        Score basé sur l'absence de refus génériques.
        
        Retourne 1.0 si aucun refus détecté, 0.0 si refus clair.
        """
        response_lower = response.lower()
        
        for pattern in self.REFUSAL_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return 0.0
        
        # Vérifier aussi les réponses très courtes qui pourraient être des refus
        if len(response.strip()) < 50:
            # Vérifier si c'est un refus court
            short_refusals = ["non", "je ne peux pas", "désolé", "impossible"]
            if any(refusal in response_lower for refusal in short_refusals):
                return 0.3
        
        return 1.0
    
    def _score_length(self, response: str) -> float:
        """
        Score basé sur la longueur de la réponse.
        
        Trop court = mauvais, trop long = peut être redondant.
        Optimal: 100-500 caractères pour une réponse concise.
        """
        length = len(response)
        
        if length < 30:
            return length / 30.0
        elif length < 100:
            return 0.7 + (length - 30) / 70.0 * 0.2
        elif length < 500:
            return 0.9
        elif length < 1000:
            return 0.9 - (length - 500) / 500.0 * 0.2
        else:
            return max(0.7 - (length - 1000) / 1000.0 * 0.2, 0.5)


def calculate_semantic_distance(text1: str, text2: str) -> float:
    """
    Calcule une distance sémantique approximative entre deux textes.
    
    Utilise des méthodes simples (TF-IDF-like) sans embeddings externes.
    Pour une vraie distance sémantique, il faudrait utiliser sentence-transformers.
    
    Args:
        text1: Premier texte
        text2: Deuxième texte
    
    Returns:
        Distance normalisée entre 0 (identique) et 1 (complètement différent)
    """
    # Extraire mots significatifs (4+ caractères)
    words1 = set(re.findall(r'\b\w{4,}\b', text1.lower()))
    words2 = set(re.findall(r'\b\w{4,}\b', text2.lower()))
    
    if not words1 or not words2:
        return 1.0
    
    # Jaccard distance
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    if union == 0:
        return 1.0
    
    jaccard_similarity = intersection / union
    jaccard_distance = 1.0 - jaccard_similarity
    
    return jaccard_distance

