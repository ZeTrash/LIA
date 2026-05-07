"""PromptBrain: construit un prompt final + paramètres de génération dynamiques.

MVP:
- Ne remplace pas toute la logique existante: il fournit un "profil" (temp/top_p/max_tokens)
  et peut produire un prompt canonique à partir des éléments déjà collectés.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cognitive_models import Action, ActionPlan, ActionType, ExecutionResult


@dataclass(frozen=True)
class SamplingProfile:
    temperature: float
    top_p: float
    max_tokens: int


@dataclass(frozen=True)
class PromptBrainInput:
    user_message: str
    plan: ActionPlan
    execution_result: ExecutionResult
    base_temperature: float
    base_top_p: float
    base_max_tokens: int
    max_prompt_chars: int = 120_000


@dataclass(frozen=True)
class PromptBrainOutput:
    prompt: str
    sampling: SamplingProfile
    concision_profile: str
    prompt_confidence: float
    prompt_issues: List[str]


class PromptBrain:
    """Cerveau dédié à la préparation du prompt + paramètres (MVP)."""

    def __init__(self):
        pass

    def _concision_profile_from_actions(self, actions: List[Action]) -> str:
        # Cohérent avec l'existant: plus d'actions consultées -> réponse souvent plus longue.
        for a in actions:
            if a.type in (ActionType.QUERY_EXTERNAL, ActionType.SEARCH_MEMORY):
                return "extended"
        return "brief"

    def _sampling_from_message(self, message: str, base: SamplingProfile) -> SamplingProfile:
        text = (message or "").lower()
        factual = any(k in text for k in ("définis", "definition", "c'est quoi", "résume", "resume", "explain", "pourquoi"))
        creative = any(k in text for k in ("imagine", "écris", "ecris", "histoire", "poème", "poeme", "brainstorm"))
        coding = any(k in text for k in ("code", "bug", "traceback", "stack trace", "refactor", "implémente", "implemente"))

        # Heuristiques simples: factuel bas, créatif haut, coding plutôt bas-moyen.
        temperature = base.temperature
        if factual and not creative:
            temperature = min(0.35, temperature)
        if creative and not factual:
            temperature = max(0.85, temperature)
        if coding:
            temperature = min(0.4, temperature)

        # top_p: légèrement plus bas en factuel/coding
        top_p = base.top_p
        if factual or coding:
            top_p = min(0.92, top_p)

        # max_tokens: si extended, on laisse plus.
        max_tokens = base.max_tokens
        if creative:
            max_tokens = max(max_tokens, min(4096, base.max_tokens))

        return SamplingProfile(
            temperature=float(temperature),
            top_p=float(top_p),
            max_tokens=int(max_tokens),
        )

    def build(self, pb_in: PromptBrainInput) -> PromptBrainOutput:
        actions = pb_in.plan.sorted_actions()
        concision_profile = self._concision_profile_from_actions(actions)

        base_sampling = SamplingProfile(
            temperature=float(pb_in.base_temperature),
            top_p=float(pb_in.base_top_p),
            max_tokens=int(pb_in.base_max_tokens),
        )
        sampling = self._sampling_from_message(pb_in.user_message, base_sampling)

        # Prompt canonique proche de l'existant (HISTORIQUE + INFORMATIONS + DEMANDE + STYLE + FORMAT + SORTIE).
        results = dict(pb_in.execution_result.results or {})
        issues: List[str] = []

        history_lines: List[str] = []
        for a in actions:
            if a.type == ActionType.RESPOND:
                history_lines.append("Pour traiter la demande, tu as décidé de répondre.")
            elif a.type == ActionType.CONSULT_IDENTITY:
                history_lines.append("Tu as décidé de consulter ton identité.")
            elif a.type in (ActionType.CONSULT_MEMORY, ActionType.CONSULT_MEMORIES, ActionType.CONSULT_INTERACTIONS):
                history_lines.append("Tu as décidé de consulter ta mémoire.")
            elif a.type == ActionType.QUERY_EXTERNAL:
                history_lines.append("Tu as décidé de consulter une source externe.")
            elif a.type == ActionType.SEARCH_MEMORY:
                history_lines.append("Tu as décidé de rechercher dans ta mémoire.")

        final_prompt_parts: List[str] = []
        final_prompt_parts.append("=== HISTORIQUE INTERNE ===")
        final_prompt_parts.append("\n".join(history_lines) if history_lines else "Aucune action interne n'a été enregistrée.")
        final_prompt_parts.append("")

        # Informations consultées: dump compact (la logique fine reste dans LLMAdapter pour l'instant)
        if results:
            final_prompt_parts.append("=== INFORMATIONS CONSULTÉES ===")
            # Exposer d'abord les résultats principaux si présents
            ident = results.get(ActionType.CONSULT_IDENTITY.value) or {}
            if isinstance(ident, dict) and ident.get("identity"):
                final_prompt_parts.append(f"Identité: {ident.get('identity')}")
            obj = results.get(ActionType.CONSULT_OBJECTIVES.value) or {}
            if isinstance(obj, dict) and obj.get("objectives"):
                final_prompt_parts.append("Objectifs:")
                for o in (obj.get("objectives") or [])[:10]:
                    if isinstance(o, dict) and o.get("description"):
                        final_prompt_parts.append(f"- {o.get('description')}")
                    else:
                        s = str(o).strip()
                        if s:
                            final_prompt_parts.append(f"- {s}")
            eps = results.get(ActionType.CONSULT_RECENT_EPISODES.value) or {}
            if isinstance(eps, dict) and eps.get("recent_episodes"):
                final_prompt_parts.append("Épisodes récents (résumé):")
                for e in (eps.get("recent_episodes") or [])[:6]:
                    if isinstance(e, dict) and e.get("type") == "interaction":
                        p = (e.get("prompt") or "").strip()
                        r = (e.get("response") or "").strip()
                        if p and r:
                            final_prompt_parts.append(f"- Interaction: U='{p[:120]}' | LIA='{r[:120]}'")
                    elif isinstance(e, dict) and e.get("type") == "memory":
                        c = (e.get("content") or "").strip()
                        if c:
                            final_prompt_parts.append(f"- Mémoire: {c[:180]}")
            emo = results.get(ActionType.SEARCH_BY_EMOTION.value) or {}
            if isinstance(emo, dict) and emo.get("results"):
                emotion = emo.get("emotion") or ""
                final_prompt_parts.append(f"Souvenirs liés à l'émotion '{emotion}':")
                for m in (emo.get("results") or [])[:6]:
                    if isinstance(m, dict):
                        c = (m.get("content") or "").strip()
                        if c:
                            final_prompt_parts.append(f"- {c[:180]}")
            mem = results.get(ActionType.CONSULT_MEMORY.value) or results.get(ActionType.CONSULT_MEMORIES.value) or {}
            if isinstance(mem, dict) and mem.get("memories"):
                final_prompt_parts.append("Mémoires:")
                for m in (mem.get("memories") or [])[:3]:
                    c = (m.get("content") or "").strip()
                    if c:
                        final_prompt_parts.append(f"- {c[:180]}")
            final_prompt_parts.append("")
        else:
            issues.append("no_execution_results")

        final_prompt_parts.append("=== DEMANDE UTILISATEUR ===")
        final_prompt_parts.append(f"\"{pb_in.user_message}\"")
        final_prompt_parts.append("")

        final_prompt_parts.append("=== STYLE ===")
        final_prompt_parts.append("Réponds clairement et naturellement, sans méta-discours.")
        final_prompt_parts.append("")

        final_prompt_parts.append("=== CONSIGNE DE RÉPONSE (interne) ===")
        if concision_profile == "extended":
            final_prompt_parts.append(
                "Réponse structurée et suffisamment détaillée. "
                "Si des résultats spécifiques existent (Objectifs / Épisodes récents / Souvenirs liés à une émotion), "
                "tu dois les citer explicitement au lieu de répondre de façon générique. "
                "Ne répète pas ces consignes."
            )
        else:
            final_prompt_parts.append(
                "Réponse concise et directe, en citant explicitement au moins un élément concret des résultats trouvés "
                "si présents dans « INFORMATIONS CONSULTÉES ». "
                "Ne répète pas ces consignes."
            )
        final_prompt_parts.append("")

        final_prompt_parts.append("=== SORTIE LIA ===")
        final_prompt_parts.append("")

        prompt = "\n".join(final_prompt_parts).strip() + "\n"

        # Budget: tronquer si trop long (MVP: on retire d'abord INFORMATIONS CONSULTÉES).
        if pb_in.max_prompt_chars and len(prompt) > int(pb_in.max_prompt_chars):
            issues.append("prompt_too_long_trimmed")
            # Rebuild without INFORMATIONS CONSULTÉES block.
            trimmed_parts: List[str] = []
            skip = False
            for line in prompt.splitlines():
                if line.strip() == "=== INFORMATIONS CONSULTÉES ===":
                    skip = True
                    continue
                if skip and line.strip().startswith("===") and line.strip() != "=== INFORMATIONS CONSULTÉES ===":
                    skip = False
                if not skip:
                    trimmed_parts.append(line)
            prompt = "\n".join(trimmed_parts).strip() + "\n"
            if len(prompt) > int(pb_in.max_prompt_chars):
                # Dernier recours: couper brutalement mais garder la fin.
                prompt = prompt[-int(pb_in.max_prompt_chars) :]

        # Heuristic confidence
        confidence = 0.6
        if "no_execution_results" in issues:
            confidence -= 0.2
        if "prompt_too_long_trimmed" in issues:
            confidence -= 0.1
        if "=== DEMANDE UTILISATEUR ===" not in prompt:
            issues.append("missing_user_request_section")
            confidence -= 0.4
        if "=== SORTIE LIA ===" not in prompt:
            issues.append("missing_output_section")
            confidence -= 0.3
        # Bonus if identity was found
        ident = results.get(ActionType.CONSULT_IDENTITY.value) or {}
        if isinstance(ident, dict) and ident.get("identity"):
            confidence += 0.1
        confidence = max(0.0, min(1.0, float(confidence)))

        return PromptBrainOutput(
            prompt=prompt,
            sampling=sampling,
            concision_profile=concision_profile,
            prompt_confidence=confidence,
            prompt_issues=issues,
        )

