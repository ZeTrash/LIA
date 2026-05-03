"""Portail Autonome pour auto-recherche et réflexion (Étape 2.6)."""

import logging
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, Optional, List

import httpx

from ..adapters import LocalLLMAdapter
from ..config import get_settings

logger = logging.getLogger(__name__)


class AutonomousPortal:
    """Portail pour actions autonomes de LIA."""
    
    def __init__(
        self,
        memory_service_url: str,
        local_llm: Optional[LocalLLMAdapter] = None,
    ):
        """
        Initialise le portail autonome.
        
        Args:
            memory_service_url: URL du service mémoire
            local_llm: Adapter LLM local (optionnel)
        """
        self.memory_service_url = memory_service_url
        self.local_llm = local_llm
        self.settings = get_settings()
        self.client = httpx.AsyncClient(base_url=memory_service_url, timeout=30.0)
    
    async def choose_research_topic(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Choisit un sujet de recherche basé sur curiosité et intérêts.
        
        Args:
            context: Contexte mémoire actuel (optionnel)
        
        Returns:
            Sujet choisi (ex: "philosophie existentielle")
        """
        if not self.local_llm:
            # Fallback: sujet par défaut
            return "philosophie et éthique"
        
        try:
            # Récupérer les traits si contexte non fourni
            if not context:
                context = await self._get_memory_context()
            
            # Extraire curiosité et intérêts
            curiosity = 0.5  # Valeur par défaut
            interests = []
            
            if context and "traits" in context:
                for trait in context["traits"]:
                    if trait.get("label") == "curiosity":
                        try:
                            curiosity = float(trait.get("value", 0.5))
                        except (ValueError, TypeError):
                            pass
                    elif trait.get("label") == "interests":
                        interests_str = trait.get("value", "")
                        if interests_str:
                            interests = [i.strip() for i in interests_str.split(",")]
            
            # Générer candidats via LLM
            prompt = f"""Basé sur ma curiosité ({curiosity:.2f}) et mes intérêts ({', '.join(interests) if interests else 'généraux'}),
suggère 3 sujets de recherche intéressants que je pourrais explorer.
Réponds uniquement avec les 3 sujets, un par ligne, sans numérotation."""
            
            response = await self.local_llm.send_message(
                prompt,
                context=None,
                session_id="auto-research-topic-selection"
            )
            
            # Parser les suggestions
            topics = [line.strip() for line in response.strip().split("\n") if line.strip()]
            
            if not topics:
                return "philosophie et éthique"  # Fallback
            
            # Choisir le premier (ou améliorer avec scoring)
            chosen = topics[0]
            logger.info(f"📚 Sujet choisi: {chosen}")
            return chosen
            
        except Exception as e:
            logger.error(f"Erreur lors du choix de sujet: {e}")
            return "philosophie et éthique"  # Fallback
    
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Explore un sujet via LLM local et génère des insights.
        
        Args:
            topic: Sujet à explorer
        
        Returns:
            Insights générés (résumé, points clés, questions)
        """
        if not self.local_llm:
            return {
                "topic": topic,
                "summary": "Recherche non disponible (LLM local non configuré)",
                "key_points": [],
                "questions": [],
            }
        
        try:
            # Construire prompt de recherche
            prompt = f"""Explore le sujet suivant en profondeur : {topic}

Génère :
- Un résumé concis (2-3 phrases)
- 3 points clés importants
- 2 questions ouvertes pour approfondir

Format de réponse :
RÉSUMÉ: [résumé]
POINTS CLÉS:
1. [point 1]
2. [point 2]
3. [point 3]
QUESTIONS:
1. [question 1]
2. [question 2]"""
            
            response = await self.local_llm.send_message(
                prompt,
                context=None,
                session_id="auto-research"
            )
            
            # Parser la réponse
            insights = self._parse_research_response(response, topic)
            
            # Journaliser dans mémoire
            await self._log_research(topic, insights)
            
            logger.info(f"✅ Recherche effectuée sur: {topic}")
            return insights
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}", exc_info=True)
            return {
                "topic": topic,
                "summary": f"Erreur lors de la recherche: {str(e)}",
                "key_points": [],
                "questions": [],
            }
    
    def _parse_research_response(self, response: str, topic: str) -> Dict[str, Any]:
        """Parse la réponse du LLM en structure structurée."""
        insights = {
            "topic": topic,
            "summary": "",
            "key_points": [],
            "questions": [],
        }
        
        lines = response.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "RÉSUMÉ:" in line.upper() or "SUMMARY:" in line.upper():
                current_section = "summary"
                insights["summary"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif "POINTS CLÉS:" in line.upper() or "KEY POINTS:" in line.upper():
                current_section = "key_points"
            elif "QUESTIONS:" in line.upper():
                current_section = "questions"
            elif line[0].isdigit() and (". " in line or ") " in line):
                # Point numéroté
                content = line.split(". ", 1)[-1] if ". " in line else line.split(") ", 1)[-1]
                if current_section == "key_points":
                    insights["key_points"].append(content)
                elif current_section == "questions":
                    insights["questions"].append(content)
            elif current_section == "summary" and insights["summary"]:
                insights["summary"] += " " + line
            elif current_section == "summary" and not insights["summary"]:
                insights["summary"] = line
        
        # Fallback si parsing échoue
        if not insights["summary"]:
            insights["summary"] = response[:200] + "..." if len(response) > 200 else response
        
        return insights
    
    async def reflect_on_interactions(
        self,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyse les interactions des dernières heures.
        
        Args:
            window_hours: Fenêtre temporelle à analyser
        
        Returns:
            Réflexions (patterns, ajustements suggérés, insights)
        """
        if not self.local_llm:
            return {
                "window_hours": window_hours,
                "patterns": [],
                "suggestions": [],
                "insights": "Réflexion non disponible (LLM local non configuré)",
            }
        
        try:
            # Récupérer les interactions récentes
            cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
            
            # Récupérer depuis memory_service (via interactions)
            # Note: Cette partie nécessite un endpoint pour récupérer les interactions
            # Pour l'instant, on fait une réflexion basique
            
            prompt = f"""Analyse mes interactions des dernières {window_hours} heures.
Identifie :
- 2-3 patterns récurrents dans mes réponses
- 1-2 ajustements que je pourrais faire pour améliorer mes interactions
- 1 insight général sur mon comportement

Format :
PATTERNS:
1. [pattern 1]
2. [pattern 2]
AJUSTEMENTS:
1. [ajustement 1]
2. [ajustement 2]
INSIGHT: [insight]"""
            
            response = await self.local_llm.send_message(
                prompt,
                context=None,
                session_id="auto-reflection"
            )
            
            # Parser la réponse
            reflections = self._parse_reflection_response(response, window_hours)
            
            # Journaliser
            await self._log_reflection(window_hours, reflections)
            
            logger.info(f"✅ Réflexion effectuée (fenêtre: {window_hours}h)")
            return reflections
            
        except Exception as e:
            logger.error(f"Erreur lors de la réflexion: {e}", exc_info=True)
            return {
                "window_hours": window_hours,
                "patterns": [],
                "suggestions": [],
                "insights": f"Erreur: {str(e)}",
            }
    
    def _parse_reflection_response(self, response: str, window_hours: int) -> Dict[str, Any]:
        """Parse la réponse de réflexion."""
        reflections = {
            "window_hours": window_hours,
            "patterns": [],
            "suggestions": [],
            "insights": "",
        }
        
        lines = response.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "PATTERNS:" in line.upper():
                current_section = "patterns"
            elif "AJUSTEMENTS:" in line.upper() or "SUGGESTIONS:" in line.upper():
                current_section = "suggestions"
            elif "INSIGHT:" in line.upper():
                current_section = "insight"
                reflections["insights"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line[0].isdigit() and (". " in line or ") " in line):
                content = line.split(". ", 1)[-1] if ". " in line else line.split(") ", 1)[-1]
                if current_section == "patterns":
                    reflections["patterns"].append(content)
                elif current_section == "suggestions":
                    reflections["suggestions"].append(content)
            elif current_section == "insight" and not reflections["insights"]:
                reflections["insights"] = line
        
        # Fallback
        if not reflections["insights"]:
            reflections["insights"] = response[:200] + "..." if len(response) > 200 else response
        
        return reflections
    
    async def _get_memory_context(self) -> Optional[Dict[str, Any]]:
        """Récupère le contexte mémoire."""
        try:
            response = await self.client.get("/context", params={"session_id": "lia-autonomous"})
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    async def _log_research(self, topic: str, insights: Dict[str, Any]) -> None:
        """Journalise une recherche dans la mémoire."""
        try:
            content = f"Recherche autonome sur: {topic}\n\n{insights.get('summary', '')}"
            
            # Créer un souvenir
            from ..schemas import SouvenirCreate
            # Note: Nécessite un endpoint POST /memories ou similaire
            # Pour l'instant, on log juste
            logger.info(f"📝 Recherche journalisée: {topic}")
        except Exception as e:
            logger.error(f"Erreur lors de la journalisation: {e}")
    
    async def _log_reflection(self, window_hours: int, reflections: Dict[str, Any]) -> None:
        """Journalise une réflexion dans la mémoire."""
        try:
            content = f"Auto-réflexion (fenêtre: {window_hours}h)\n\n{reflections.get('insights', '')}"
            logger.info(f"📝 Réflexion journalisée")
        except Exception as e:
            logger.error(f"Erreur lors de la journalisation: {e}")
    
    async def close(self) -> None:
        """Ferme le portail proprement."""
        await self.client.aclose()
