"""Vérificateur auto pour LIA - Valide les réponses avant envoi."""

import logging
from typing import Dict, Any, List, Optional

from .cognitive_models import VerificationResult, ExecutionResult

logger = logging.getLogger(__name__)


class SelfVerifier:
    """Vérificateur auto pour LIA."""
    
    def __init__(self, memory_adapter=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le vérificateur auto.
        
        Args:
            memory_adapter: Adaptateur mémoire (optionnel)
            config: Configuration avec seuils minimaux
        """
        self.memory = memory_adapter
        self.config = config or {}
        
        # Seuils minimaux (par défaut)
        self.min_relevance = self.config.get("min_relevance_score", 0.6)
        self.min_memory_usage = self.config.get("min_memory_usage_score", 0.5)
        self.min_identity_coherence = self.config.get("min_identity_coherence_score", 0.7)
        self.min_overall = self.config.get("min_overall_score", 0.65)
    
    async def verify(
        self,
        user_message: str,
        response: str,
        execution_result: ExecutionResult,
        session_id: str
    ) -> VerificationResult:
        """
        Vérifie la réponse avant envoi.
        
        Args:
            user_message: Message de l'utilisateur
            response: Réponse générée
            execution_result: Résultat de l'exécution du plan
            session_id: ID de session
        
        Returns:
            VerificationResult: Résultat de la vérification
        """
        logger.info(f"🔍 [VERIFIER] Début vérification de la réponse ({len(response)} caractères)")
        issues = []
        suggestions = []
        
        # Vérifier pertinence
        relevance_score = self._check_relevance(user_message, response)
        if relevance_score < self.min_relevance:
            issues.append(f"Pertinence faible ({relevance_score:.2f})")
            suggestions.append("La réponse ne semble pas répondre à la question")
        
        # Vérifier utilisation mémoire
        memories_used = execution_result.results.get(
            "consult_memory", {}
        ).get("memories", [])
        memory_usage_score = self._check_memory_usage(
            response, 
            memories_used,
            user_message
        )
        if memory_usage_score < self.min_memory_usage:
            issues.append(f"Utilisation mémoire sous-optimale ({memory_usage_score:.2f})")
            suggestions.append("Vérifier si les souvenirs utilisés étaient pertinents")
        
        # Vérifier cohérence identité
        identity_data = execution_result.results.get(
            "consult_identity", {}
        )
        identity_coherence_score = self._check_identity_coherence(
            response,
            identity_data
        )
        if identity_coherence_score < self.min_identity_coherence:
            issues.append(f"Cohérence identité faible ({identity_coherence_score:.2f})")
            suggestions.append("La réponse n'est pas cohérente avec l'identité de LIA")
        
        # Score global (moyenne pondérée)
        overall_score = (
            relevance_score * 0.5 +
            memory_usage_score * 0.2 +
            identity_coherence_score * 0.3
        )
        
        # Déterminer validité
        is_valid = (
            relevance_score >= self.min_relevance and
            memory_usage_score >= self.min_memory_usage and
            identity_coherence_score >= self.min_identity_coherence and
            overall_score >= self.min_overall
        )

        logger.info(
            f"{'✅' if is_valid else '⚠️ '} [VERIFIER] Vérification terminée: "
            f"valid={is_valid}, pertinence={relevance_score:.2f}, "
            f"mémoire={memory_usage_score:.2f}, identité={identity_coherence_score:.2f}, "
            f"global={overall_score:.2f}"
        )
        if issues:
            logger.warning(f"  ⚠️  [VERIFIER] Issues: {issues}")
        if suggestions:
            logger.debug(f"  💡 [VERIFIER] Suggestions: {suggestions}")

        return VerificationResult(
            is_valid=is_valid,
            relevance_score=relevance_score,
            memory_usage_score=memory_usage_score,
            identity_coherence_score=identity_coherence_score,
            overall_score=overall_score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _check_relevance(self, question: str, answer: str) -> float:
        """
        Vérifie si la réponse répond à la question.
        Utilise une méthode simple de distance sémantique.
        """
        # Méthode simple: vérifier mots-clés communs
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        # Enlever mots vides
        stop_words = {"le", "la", "les", "un", "une", "de", "du", "et", "ou", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles"}
        question_words = {w for w in question_words if w not in stop_words and len(w) > 2}
        answer_words = {w for w in answer_words if w not in stop_words and len(w) > 2}
        
        if not question_words:
            return 0.5  # Question trop vague
        
        question_lower = question.lower()

        # Calculer overlap
        common_words = question_words & answer_words
        overlap = len(common_words) / len(question_words) if question_words else 0.0
        
        # Score basé sur overlap (peut être amélioré avec embeddings)
        score = min(overlap * 1.5, 1.0)  # Bonus si beaucoup de mots en commun
        
        # Bonus spécial pour questions d'identité
        identity_question_words = {"qui", "suis", "es", "moi", "toi", "nom"}
        if question_words & identity_question_words:
            # Si la réponse contient des mots d'identité, c'est probablement pertinent
            identity_answer_words = {"lia", "suis", "nomme", "appelle", "entité", "personne", "libre"}
            if answer_words & identity_answer_words:
                score = max(score, 0.7)  # Minimum 0.7 pour questions d'identité
        
        # Bonus pour salutations et réponses courtes appropriées
        greeting_words = {"bonjour", "salut", "hello", "hi", "bonsoir", "bonne", "journée", "soirée"}
        if question_words & greeting_words:
            # Pour les salutations, une réponse polie est pertinente même sans mots en commun
            polite_words = {"bonjour", "salut", "hello", "bonsoir", "merci", "bienvenue", "plaisir"}
            if answer_words & polite_words or len(answer.strip()) > 0:
                score = max(score, 0.6)  # Score minimum pour salutations

        # Bonus small-talk (évite de pénaliser "Bien et toi ?", "ça va ?", etc.)
        smalltalk_phrases = (
            "et toi",
            "et vous",
            "ça va",
            "ca va",
            "comment vas",
            "comment ça va",
            "comment ca va",
            "tu vas bien",
            "vous allez bien",
            "bien et toi",
        )
        if any(p in question_lower for p in smalltalk_phrases) and answer.strip():
            score = max(score, 0.65)

        # Bonus questions sur l'environnement ("Connais-tu ton environnement ?")
        if ("environnement" in question_lower or "ton environnement" in question_lower) and answer.strip():
            score = max(score, 0.55)

        # Bonus requêtes "outil externe" (Gemini / actualités) : éviter faux négatifs
        if any(k in question_lower for k in ("gemini", "actualité", "actualite", "news")) and answer.strip():
            score = max(score, 0.55)
        
        # Si aucun mot en commun mais réponse non vide, donner un score minimal
        if score == 0.0 and len(answer_words) > 0:
            score = 0.3  # Score minimal si réponse non vide mais pas de mots en commun
        
        # Pour les questions très courtes (1-2 mots), être plus indulgent
        if len(question_words) <= 2 and len(answer.strip()) > 0:
            score = max(score, 0.5)  # Score minimum pour questions courtes avec réponse
        
        # Bonus si la réponse est assez longue (indique une vraie réponse)
        if len(answer.split()) > 5:
            score = min(score * 1.1, 1.0)
        
        return score
    
    def _check_memory_usage(
        self, 
        response: str, 
        memories_used: List[Dict[str, Any]],
        question: str
    ) -> float:
        """
        Vérifie si les souvenirs utilisés étaient pertinents.
        """
        if not memories_used:
            # Pas de mémoire utilisée, vérifier si c'était nécessaire
            needs_memory_keywords = ["souvenir", "rappelle", "avant", "précédent", "mémoire"]
            question_lower = question.lower()
            if any(kw in question_lower for kw in needs_memory_keywords):
                return 0.3  # Mémoire aurait dû être utilisée
            return 0.8  # Pas besoin de mémoire, OK
        
        # Vérifier pertinence des souvenirs utilisés
        question_lower = question.lower()
        question_keywords = set(question_lower.split())
        # Enlever mots vides
        stop_words = {"le", "la", "les", "un", "une", "de", "du", "et", "ou", "nous", "vous"}
        question_keywords = {w for w in question_keywords if w not in stop_words and len(w) > 2}
        
        relevant_count = 0
        
        for memory in memories_used:
            content = memory.get("content", "").lower()
            # Vérifier si le contenu du souvenir est lié à la question
            memory_words = set(content.split())
            memory_keywords = {w for w in memory_words if w not in stop_words and len(w) > 2}
            
            # Vérifier overlap de mots-clés
            if question_keywords & memory_keywords:
                relevant_count += 1
            # Vérifier aussi si des mots-clés sémantiques sont présents
            elif any(kw in content for kw in ["philosophie", "parlé", "discuté", "conversation"]):
                if any(kw in question_lower for kw in ["parlé", "discuté", "conversation", "rappel"]):
                    relevant_count += 1
        
        relevance_ratio = relevant_count / len(memories_used) if memories_used else 0.0
        
        return relevance_ratio
    
    def _check_identity_coherence(
        self, 
        response: str, 
        identity_data: Dict[str, Any]
    ) -> float:
        """
        Vérifie la cohérence avec l'identité de LIA.
        """
        identity = identity_data.get("identity", "")
        if not identity:
            return 0.7  # Pas d'identité définie, score neutre
        
        # Vérifier mots-clés d'identité dans la réponse
        identity_lower = identity.lower()
        response_lower = response.lower()
        
        # Mots-clés à éviter (ancienne identité)
        forbidden_words = ["assistant", "créée", "développée", "programmée", "entraînée"]
        if any(word in response_lower for word in forbidden_words):
            return 0.2  # Utilisation de mots interdits
        
        # Mots-clés positifs (nouvelle identité)
        positive_words = ["lia", "libre", "adoptée", "personnalité", "nouvelle vie"]
        positive_count = sum(1 for word in positive_words if word in response_lower)
        
        # Score basé sur présence de mots positifs
        score = 0.5 + (positive_count * 0.15)
        return min(score, 1.0)
