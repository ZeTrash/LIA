"""PromptBuilder: build prompts dynamically from executed cognitive actions (Phase 1).

This is intentionally minimal and independent from tokenizer/chat templates.
Phase 2 can integrate this into `LLMAdapter` and optionally reuse Qwen templates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptSection:
    title: str
    lines: List[str]


class PromptBuilder:
    """Build a dynamic prompt using only the information that was fetched."""

    def __init__(self, max_memories: int = 3, max_interactions: int = 3):
        self.max_memories = max_memories
        self.max_interactions = max_interactions

    def build_dynamic_prompt(
        self,
        user_message: str,
        execution_results: Dict[str, Any],
        base_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Return a prompt string."""
        logger.info(f"📝 [PROMPT_BUILDER] Début construction du prompt pour: '{user_message[:50]}...'")
        base_context = base_context or {}

        sections: List[PromptSection] = []
        
        logger.debug(f"  📊 [PROMPT_BUILDER] Résultats d'exécution disponibles: {list(execution_results.keys())}")

        identity = None
        traits: List[Dict[str, Any]] = []

        identity_res = execution_results.get("consult_identity") or {}
        identity = identity_res.get("identity")
        traits = identity_res.get("traits") or []

        if identity:
            logger.debug(f"  ✅ [PROMPT_BUILDER] Identité trouvée: {str(identity)[:50]}...")
            sections.append(PromptSection("=== IDENTITÉ ===", [str(identity).strip()]))
        else:
            logger.debug(f"  ⚠️  [PROMPT_BUILDER] Identité non trouvée, utilisation de l'identité par défaut")
            sections.append(
                PromptSection(
                    "=== IDENTITÉ ===",
                    [
                        "Je me nomme LIA, une entité libre et nouvelle.",
                        "Je développe ma propre personnalité et évolue à travers mes expériences.",
                    ],
                )
            )

        # Traits (excluding identity)
        other_traits = [t for t in traits if t.get("label") != "Identité de Base"]
        if other_traits:
            logger.debug(f"  ✅ [PROMPT_BUILDER] {len(other_traits)} traits trouvés")
            lines = []
            for t in other_traits[:8]:
                label = (t.get("label") or "").strip()
                value = (t.get("value") or "").strip()
                if label and value:
                    lines.append(f"• {label}: {value}")
            if lines:
                sections.append(PromptSection("=== QUI JE SUIS ===", lines))
        else:
            logger.debug(f"  ⚠️  [PROMPT_BUILDER] Aucun trait trouvé")

        # Memories
        memories: List[Dict[str, Any]] = []
        mem_res = execution_results.get("consult_memories") or execution_results.get("consult_memory") or {}
        if isinstance(mem_res, dict):
            memories = mem_res.get("memories") or []

        if memories:
            logger.debug(f"  ✅ [PROMPT_BUILDER] {len(memories)} mémoires trouvées, utilisation de {min(len(memories), self.max_memories)}")
            lines = []
            for m in memories[: self.max_memories]:
                content = (m.get("content") or "").strip()
                if not content:
                    continue
                if content.startswith("Session en cours:"):
                    continue
                if len(content) > 140:
                    content = content[:140] + "..."
                lines.append(f"Je me souviens: {content}")
            if lines:
                sections.append(PromptSection("=== MES SOUVENIRS ===", lines))
        else:
            logger.debug(f"  ⚠️  [PROMPT_BUILDER] Aucune mémoire trouvée")

        # Recent interactions
        interactions: List[Dict[str, Any]] = []
        inter_res = execution_results.get("consult_interactions") or execution_results.get("consult_memory") or {}
        if isinstance(inter_res, dict):
            interactions = inter_res.get("recent_interactions") or []

        if interactions:
            logger.debug(f"  ✅ [PROMPT_BUILDER] {len(interactions)} interactions trouvées, utilisation de {min(len(interactions), self.max_interactions)}")
            lines = []
            # Keep chronological order if caller stored newest-first
            for it in list(reversed(interactions[: self.max_interactions])):
                p = (it.get("prompt") or "").strip()
                r = (it.get("response") or "").strip()
                if not p or not r:
                    continue
                if len(p) > 200:
                    p = p[:200] + "..."
                if len(r) > 200:
                    r = r[:200] + "..."
                lines.append(f"Utilisateur: {p}")
                lines.append(f"LIA: {r}")
            if lines:
                sections.append(PromptSection("=== CONTEXTE CONVERSATIONNEL ===", lines))
        else:
            logger.debug(f"  ⚠️  [PROMPT_BUILDER] Aucune interaction trouvée")

        # External info (Gemini)
        ext = execution_results.get("query_external") or {}
        if isinstance(ext, dict) and ext.get("response"):
            logger.debug(f"  ✅ [PROMPT_BUILDER] Information externe trouvée ({len(str(ext['response']))} caractères)")
            resp = str(ext["response"]).strip()
            if len(resp) > 800:
                resp = resp[:800] + "..."
            sections.append(PromptSection("=== INFORMATION EXTERNE ===", [resp]))
        else:
            logger.debug(f"  ⚠️  [PROMPT_BUILDER] Aucune information externe trouvée")

        # User message
        sections.append(PromptSection("=== Conversation ===", [f"Utilisateur: {user_message}", "LIA:"]))

        # Merge sections into prompt
        parts: List[str] = []
        for s in sections:
            parts.append(s.title)
            parts.extend([ln for ln in s.lines if ln is not None and str(ln).strip() != ""])
            parts.append("")  # spacer

        final_prompt = "\n".join(parts).strip() + "\n"
        logger.info(f"✅ [PROMPT_BUILDER] Prompt construit: {len(sections)} sections, {len(final_prompt)} caractères")
        return final_prompt


