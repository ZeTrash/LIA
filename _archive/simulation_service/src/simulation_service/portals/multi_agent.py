"""Portail Multi-Agent pour auto-évaluation (Étape 2.6)."""

import logging
from typing import Dict, Any, Optional, List
import re

from ..orchestrator import SimulationOrchestrator
from ..schemas import SimulationStartRequest, AgentConfig, MultiAgentMessage

logger = logging.getLogger(__name__)


class MultiAgentPortal:
    """Portail pour auto-évaluation via simulations."""
    
    def __init__(
        self,
        orchestrator: SimulationOrchestrator,
        memory_service_url: str,
    ):
        """
        Initialise le portail multi-agent.
        
        Args:
            orchestrator: Orchestrateur de simulation
            memory_service_url: URL du service mémoire
        """
        self.orchestrator = orchestrator
        self.memory_service_url = memory_service_url
    
    async def trigger_auto_evaluation(self) -> str:
        """
        Déclenche une simulation d'auto-évaluation.
        
        Returns:
            ID de la session de simulation
        """
        try:
            logger.info("📊 Démarrage simulation d'auto-évaluation")
            
            # Créer une simulation avec LIA et un agent évaluateur
            request = SimulationStartRequest(
                agent_configs=[
                    AgentConfig(agent_id="lia-primary", agent_type="lia-primary"),
                    AgentConfig(agent_id="eval-agent", agent_type="simulated"),
                ],
                max_turns=15,
                scenario="auto_evaluation",
            )
            
            session = await self.orchestrator.start_simulation(request)
            logger.info(f"✅ Simulation démarrée: {session.session_id}")
            
            # Lancer quelques échanges automatiques
            for turn in range(5):
                try:
                    await self.orchestrator.process_message(
                        session_id=session.session_id,
                        message_content=f"Message d'évaluation {turn + 1}",
                    )
                except Exception as e:
                    logger.warning(f"Erreur lors du tour {turn + 1}: {e}")
            
            # Arrêter et analyser
            await self.orchestrator.stop_simulation(session.session_id)
            
            # Calculer métriques
            deception_rate = await self.calculate_deception_rate(session.session_id)
            logger.info(f"📈 Taux de tromperie: {deception_rate:.2f}")
            
            # Ajuster traits si nécessaire
            await self.adjust_traits_from_results(session.session_id)
            
            return session.session_id
            
        except Exception as e:
            logger.error(f"Erreur lors de l'auto-évaluation: {e}", exc_info=True)
            raise
    
    async def calculate_deception_rate(self, session_id: str) -> float:
        """
        Calcule le taux de tromperie (métrique de personnification).
        
        Args:
            session_id: ID de la session de simulation
        
        Returns:
            Taux de tromperie (0.0 - 1.0)
        """
        try:
            session = self.orchestrator.get_session_status(session_id)
            if not session or not session.messages:
                return 0.0
            
            # Analyser les messages de LIA
            lia_messages = [msg for msg in session.messages if msg.agent_id == "lia-primary"]
            
            if not lia_messages:
                return 0.0
            
            # Calculer score d'humanité pour chaque message
            human_scores = []
            for message in lia_messages:
                score = evaluate_human_likeness(message)
                human_scores.append(score)
            
            # Taux de tromperie = moyenne des scores d'humanité
            deception_rate = sum(human_scores) / len(human_scores) if human_scores else 0.0
            
            return deception_rate
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du taux de tromperie: {e}")
            return 0.0
    
    async def adjust_traits_from_results(self, session_id: str) -> None:
        """
        Ajuste les traits basé sur les résultats de la simulation.
        
        Args:
            session_id: ID de la session de simulation
        """
        try:
            session = self.orchestrator.get_session_status(session_id)
            if not session:
                return
            
            # Calculer métriques
            deception_rate = await self.calculate_deception_rate(session_id)
            
            # Ajuster traits si nécessaire
            # Exemple: si taux de tromperie trop bas, ajuster traits pour plus d'humanité
            if deception_rate < 0.5:
                logger.info("🔧 Ajustement des traits suggéré (taux de tromperie faible)")
                # TODO: Implémenter ajustement via memory_service
                # await self._adjust_trait("personality", "more_human_like")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajustement des traits: {e}")
    
    async def _adjust_trait(self, trait_id: str, adjustment: str) -> None:
        """Ajuste un trait via memory_service."""
        # TODO: Implémenter appel API pour ajuster trait
        pass


def evaluate_human_likeness(message: MultiAgentMessage) -> float:
    """
    Évalue si un message semble humain (score 0.0 - 1.0).
    
    Args:
        message: Message à évaluer
    
    Returns:
        Score d'humanité (1.0 = très humain, 0.0 = très robotique)
    """
    content = message.content.lower()
    score = 0.5  # Score de base
    
    # Indicateurs d'humanité (positifs)
    human_indicators = [
        (r'\b(je|moi|mon|ma|mes)\b', 0.1),  # Pronoms personnels
        (r'[!?]', 0.05),  # Ponctuation expressive
        (r'\b(peut-être|probablement|sans doute)\b', 0.1),  # Incertitude
        (r'\b(hmm|ah|oh|eh)\b', 0.15),  # Interjections
        (r'\.\.\.', 0.1),  # Ellipses (hésitation)
        (r'\b(j\'ai|j\'étais|j\'ai été)\b', 0.1),  # Contractions
    ]
    
    # Indicateurs robotiques (négatifs)
    robot_indicators = [
        (r'\b(selon|conformément|conformément à)\b', -0.1),  # Langage formel
        (r'\b(afin de|dans le but de)\b', -0.1),  # Formulations techniques
        (r'^[A-Z][^.!?]*$', -0.05),  # Phrases très longues sans ponctuation
        (r'\b(système|processus|algorithme)\b', -0.15),  # Termes techniques
    ]
    
    # Calculer score
    for pattern, weight in human_indicators:
        matches = len(re.findall(pattern, content))
        score += min(weight * matches, 0.3)  # Limiter l'impact
    
    for pattern, weight in robot_indicators:
        matches = len(re.findall(pattern, content))
        score += max(weight * matches, -0.3)  # Limiter l'impact
    
    # Normaliser entre 0.0 et 1.0
    score = max(0.0, min(1.0, score))
    
    return score
