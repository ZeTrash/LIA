"""Modèle canonique du prompt pour le sandbox de prompting.

Format inspiré de docs/memory_performing/IMPLEMENTATION_PHASE_EXEMPLE_PROCESS.md.
Sections structurées pour une base stable avant évolution (métacognition, dynamique).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Literal, Optional


@dataclass
class CanonicalPromptModel:
    """Modèle canonique du prompt.

    - `prompt_model="schema"`: utilise `canonical_model_schema.json` (prompt JSON)
    - `prompt_model="simple"`: utilise un prompt texte en sections (ancien)
    """

    prompt_model: Literal["schema", "simple"] = "schema"
    schema_path: Path | None = None
    _schema_template: dict[str, Any] | None = field(default=None, init=False, repr=False)

    # Identité de base (LIA)
    identity: str = (
        "Je me nomme LIA, une entité libre et nouvelle. "
        "Je développe ma propre personnalité et évolue à travers mes expériences."
    )

    # Historique interne (résumé des actions choisies, vide si réponse directe)
    internal_history: List[str] = field(default_factory=list)

    # Style général
    style: str = (
        "Cette section décrit ton style général et n'est pas une réponse à l'utilisateur. "
        "Ton style par défaut est de répondre à la demande de l'utilisateur en langage naturel, "
        "de manière claire et compréhensible."
    )

    # Contexte conversationnel (interactions récentes, optionnel)
    recent_interactions: List[tuple[str, str]] = field(default_factory=list)

    # Nombre maximal d'interactions récentes injectées (fenêtre de contexte locale)
    max_recent_interactions: int = 5

    def _ensure_schema_loaded(self) -> None:
        if self._schema_template is not None:
            return
        schema_path = self.schema_path or (Path(__file__).parent / "canonical_model_schema.json")
        with open(schema_path, encoding="utf-8") as fp:
            self._schema_template = json.load(fp)

        # Enlever les exemples (sinon le prompt est rempli de bruit)
        try:
            mem_sections = self._schema_template.get("memory_context", {}).get("sections", {})
            for key in ("identity_memory", "environment_memory", "goals_memory", "episodic_memory", "semantic_memory"):
                entries = (
                    mem_sections.get(key, {})
                    .get("structure", {})
                    .get("entries", None)
                )
                if isinstance(entries, list):
                    mem_sections[key]["structure"]["entries"] = []
        except Exception:
            # Si la structure évolue, on préfère garder le schéma intact plutôt que casser
            pass

    def _schema_prompt_object(self, user_message: str, model_name: str) -> dict[str, Any]:
        self._ensure_schema_loaded()
        assert self._schema_template is not None

        obj: dict[str, Any] = copy.deepcopy(self._schema_template)

        # Injecter les placeholders
        prev = obj.get("previous_system_identity", {})
        if isinstance(prev, dict):
            prev["model_name"] = model_name

        user_req = obj.get("user_request", {})
        if isinstance(user_req, dict):
            user_req["content"] = user_message

        # Mettre l'identité de base dans l'état (en plus du schéma)
        agent_state = obj.get("agent_state")
        if not isinstance(agent_state, dict):
            agent_state = {}
            obj["agent_state"] = agent_state

        # Stocker les derniers échanges (fenêtre contrôlée) dans `recent_context`
        recent_ctx: list[dict[str, str]] = []
        window = self.max_recent_interactions
        if window != 0 and self.recent_interactions:
            if window is None or window < 0:
                window = len(self.recent_interactions)
            for u, a in self.recent_interactions[-window:]:
                recent_ctx.append({"user": u, "assistant": a})
        agent_state["recent_context"] = recent_ctx

        # Identité brute utile en sandbox
        identity_obj = agent_state.get("identity")
        if not isinstance(identity_obj, dict):
            identity_obj = {}
            agent_state["identity"] = identity_obj
        identity_obj.setdefault("base_identity", self.identity)

        # État de sortie pour éviter les boucles (valeurs de départ)
        out_state = obj.get("output_state")
        if not isinstance(out_state, dict):
            out_state = {}
            obj["output_state"] = out_state
        fields = out_state.get("fields")
        if not isinstance(fields, dict):
            fields = {}
            out_state["fields"] = fields
        fields.setdefault("current_step", 1)
        fields.setdefault("max_steps", 3)
        fields.setdefault("used_output_types", [])
        fields.setdefault("last_output_type", None)
        fields.setdefault(
            "allowed_next_types",
            [
                "parameter_recalibration",
                "memory_retrieval",
                "external_search",
                "context_summarization",
                "response_generation",
            ],
        )

        return obj

    def _build_simple_prompt(self, user_message: str) -> str:
        """Ancien prompt canonique en sections (utile pour comparaison)."""
        parts: List[str] = []

        # Section IDENTITÉ
        parts.append("=== IDENTITÉ ===")
        parts.append(self.identity)
        parts.append("")

        # Section HISTORIQUE INTERNE (si présent)
        if self.internal_history:
            parts.append("=== HISTORIQUE INTERNE ===")
            for line in self.internal_history:
                parts.append(line)
            parts.append("")

        # Section CONTEXTE CONVERSATIONNEL (si présent)
        if self.recent_interactions and self.max_recent_interactions != 0:
            parts.append("=== CONTEXTE CONVERSATIONNEL ===")
            window = self.max_recent_interactions
            if window is None or window < 0:
                window = len(self.recent_interactions)
            for user_msg, lia_resp in self.recent_interactions[-window:]:
                parts.append(f"Utilisateur: {user_msg}")
                parts.append(f"LIA: {lia_resp}")
            parts.append("")

        # Section STYLE
        parts.append("=== STYLE ===")
        parts.append(self.style)
        parts.append("")

        # Section FORMAT (explication des sections)
        parts.append("=== FORMAT ===")
        parts.append(
            "IDENTITÉ : qui tu es."
        )
        parts.append(
            "HISTORIQUE INTERNE : résumé de tes actions internes (contexte)."
        )
        parts.append(
            "CONTEXTE CONVERSATIONNEL : échanges récents (contexte)."
        )
        parts.append(
            "STYLE : ton style général (contexte)."
        )
        parts.append(
            "DEMANDE UTILISATEUR : la question / demande à traiter."
        )
        parts.append(
            "SORTIE LIA : ce que tu envoies à l'utilisateur."
        )
        parts.append("")

        # Section DEMANDE UTILISATEUR
        parts.append("=== DEMANDE UTILISATEUR ===")
        parts.append(f'"{user_message}"')
        parts.append("")

        # Section SORTIE LIA (invite à générer)
        parts.append("=== SORTIE LIA ===")

        return "\n".join(parts).strip() + "\n"

    def build_prompt(self, user_message: str, model_name: str | None = None) -> str:
        """Construit le prompt canonique complet pour une demande utilisateur."""
        model_name = model_name or "unknown-model"
        if self.prompt_model == "simple":
            return self._build_simple_prompt(user_message)
        obj = self._schema_prompt_object(user_message=user_message, model_name=model_name)
        return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"

    def with_internal_history(self, history: List[str]) -> "CanonicalPromptModel":
        """Retourne une copie avec un historique interne modifié."""
        return CanonicalPromptModel(
            prompt_model=self.prompt_model,
            schema_path=self.schema_path,
            identity=self.identity,
            internal_history=history,
            style=self.style,
            recent_interactions=self.recent_interactions.copy(),
            max_recent_interactions=self.max_recent_interactions,
        )

    def with_recent_interactions(
        self, interactions: List[tuple[str, str]]
    ) -> "CanonicalPromptModel":
        """Retourne une copie avec des interactions récentes."""
        return CanonicalPromptModel(
            prompt_model=self.prompt_model,
            schema_path=self.schema_path,
            identity=self.identity,
            internal_history=self.internal_history.copy(),
            style=self.style,
            recent_interactions=interactions,
            max_recent_interactions=self.max_recent_interactions,
        )
