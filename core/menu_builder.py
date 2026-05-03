"""MenuBuilder : construction des menus base/général/spécifiques.

Ce module encapsule la logique de construction des menus en s'appuyant sur :
- MemoryRankNavigator (priorisation mémoire),
- SemanticSearcher (recherche sémantique),
- ContextualActionFilter (filtrage contextuel),
- PatternLearner (recommandations de patterns, à intégrer ensuite).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from .cognitive_models import Action, ActionType
from .memory_rank_navigator import MemoryRankNavigator
from .semantic_searcher import SemanticSearcher
from .contextual_action_filter import ContextualActionFilter

logger = logging.getLogger(__name__)


ConfigType = Union[Dict[str, Any], Any]


class MenuBuilder:
    """Construit les menus adaptés au contexte et à la mémoire."""

    def __init__(
        self,
        memory_store: Any,
        pattern_learner: Optional[Any] = None,
        config: Optional[ConfigType] = None,
    ):
        """
        Initialise le MenuBuilder.

        Args:
            memory_store: Store pour accéder à la mémoire MemoryRank
            pattern_learner: PatternLearner pour obtenir les recommandations de patterns
                             (utilise Groq/Gemini pour l'apprentissage)
            config: Configuration planner (dict ou PlannerConfig)
        """
        self.memory_store = memory_store
        self.pattern_learner = pattern_learner
        self.config = config or {}

        self.navigator = MemoryRankNavigator(memory_store=memory_store)
        self.searcher = SemanticSearcher(memory_store=memory_store)
        self.action_filter = ContextualActionFilter()

    def _get_config_value(self, key: str, default: Any) -> Any:
        """Récupère une valeur de config depuis dict ou objet PlannerConfig."""
        cfg = self.config
        if isinstance(cfg, dict):
            return cfg.get(key, default)
        return getattr(cfg, key, default)

    def _pattern_rec_action_type(self, rec_code: str, menu_context: str) -> Optional[ActionType]:
        """Mappe un code pattern (B*/G*) vers un ActionType."""
        rec_code = (rec_code or "").strip().upper()
        ctx = (menu_context or "").strip().lower() or "base"
        if ctx == "base":
            if rec_code == "B1":
                return ActionType.CONSULT_REQUEST
            if rec_code == "B2":
                return ActionType.NAVIGATE_GENERAL
            if rec_code == "B3":
                return ActionType.RESPOND
            return None
        # general
        if rec_code == "G1":
            return ActionType.CONSULT_IDENTITY
        if rec_code == "G2":
            return ActionType.CONSULT_TRAITS
        if rec_code == "G3":
            return ActionType.CONSULT_ENVIRONMENT
        if rec_code == "G4":
            return ActionType.CONSULT_MEMORY
        if rec_code == "G5":
            return ActionType.RESPOND
        if rec_code == "G6":
            return ActionType.NAVIGATE_BASE
        return None

    def _reorder_with_recommendation(self, actions: List[Action], recommended: Optional[ActionType]) -> List[Action]:
        """Place l'action recommandée en tête (ordre stable)."""
        if not actions or not recommended:
            return actions
        for i, a in enumerate(actions):
            if a.type == recommended:
                return [a] + actions[:i] + actions[i + 1 :]
        return actions

    # --- MENUS ---

    def build_base_menu(
        self,
        user_message: str,
        execution_results: Dict[str, Any],
        session_id: str,
    ) -> List[Action]:
        """Construit le menu de base avec actions adaptées.

        Structure actuelle (alignée sur CognitivePlanner.build_action_menu) :
        1) CONSULTER_REQUEST (si pas déjà fait)
        2) NAVIGATE_GENERAL
        3) RESPOND
        """
        _ = session_id
        theme = (execution_results.get("_theme_pattern") or "").strip() or None
        prev_step = "initial"

        actions: List[Action] = []
        priority = 1

        def _already_done(action_value: str) -> bool:
            return action_value in execution_results

        # 2) Voir la demande utilisateur
        if not _already_done(ActionType.CONSULT_REQUEST.value):
            actions.append(
                Action(
                    ActionType.CONSULT_REQUEST,
                    {"request": user_message},
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        # 3) Aller au menu général
        # Hint: densité mémoire (pour debug/logs)
        hint_parts: List[str] = []
        try:
            mem_count = len(self.navigator.get_top_memories(limit=50))
            trait_count = len(self.navigator.get_top_traits(limit=50))
            if mem_count:
                hint_parts.append(f"mem≈{mem_count}")
            if trait_count:
                hint_parts.append(f"traits≈{trait_count}")
            if theme:
                hint_parts.append(f"theme={theme}")
        except Exception:
            pass

        actions.append(
            Action(
                ActionType.NAVIGATE_GENERAL,
                {"_hint": ", ".join(hint_parts)} if hint_parts else {},
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # 4) Toujours permettre de répondre
        actions.append(
            Action(
                ActionType.RESPOND,
                {},
                priority=priority,
                required=True,
            )
        )

        # Filtrage contextuel (éviter certaines répétitions)
        filtered = self.action_filter.filter_actions(
            actions=actions,
            execution_results=execution_results,
            user_request=user_message,
        )

        # Recommandation via patterns V2 (si disponible en DB via MemoryStore)
        recommended_action: Optional[ActionType] = None
        try:
            if hasattr(self.memory_store, "get_pattern_recommendation"):
                rec = self.memory_store.get_pattern_recommendation(
                    menu_context="base",
                    prev_step=prev_step,
                    theme_pattern=theme,
                )
                if rec and rec.get("recommended_step"):
                    recommended_action = self._pattern_rec_action_type(str(rec["recommended_step"]), "base")
        except Exception:
            recommended_action = None

        return self._reorder_with_recommendation(filtered, recommended_action)

    def build_general_menu(
        self,
        user_message: str,
        execution_results: Dict[str, Any],
        session_id: str,
    ) -> List[Action]:
        """Construit le menu général (connaissance de soi)."""
        _ = session_id
        theme = (execution_results.get("_theme_pattern") or "").strip() or None
        prev_step = "initial"

        actions: List[Action] = []
        priority = 1

        def _already_done(action_value: str) -> bool:
            return action_value in execution_results

        # --- Pré-calculs MemoryRank/semantic (hints) ---
        identity_preview: List[str] = []
        traits_preview: List[str] = []
        mem_preview: List[str] = []
        search_preview: List[str] = []
        trait_count_est = 0
        mem_count_est = 0

        try:
            id_items = self.navigator.get_identity_phrases(limit=3)
            identity_preview = [str(x.get("content") or "")[:80] for x in id_items if (x.get("content") or "")]
        except Exception:
            pass

        try:
            t_items = self.navigator.get_top_traits(limit=50)
            trait_count_est = len(t_items)
            traits_preview = [
                f"{(t.get('label') or '')} (w={float(t.get('weight') or 0.0):.1f})"
                for t in t_items[:3]
                if t.get("label")
            ]
        except Exception:
            pass

        try:
            m_items = self.navigator.get_top_memories(limit=50)
            mem_count_est = len(m_items)
            mem_preview = [str(m.get("content") or "")[:80] for m in m_items[:3] if (m.get("content") or "")]
        except Exception:
            pass

        try:
            s_items = self.searcher.search(query=user_message, limit=3)
            search_preview = [
                str(m.get("content") or "")[:80] for m in s_items[:3] if (m.get("content") or "")
            ]
        except Exception:
            pass

        # --- N dynamiques ---
        # Traits: au moins 5, au plus 20, borné par le nombre dispo estimé
        traits_limit = max(5, min(20, trait_count_est or 20))
        # Mémoire: plus large si thème "mémoire"
        base_mem_limit = int(self._get_config_value("default_memory_limit", 5))
        if theme and theme.lower() in {"mémoire", "memory", "rappel", "souvenir"}:
            base_mem_limit = max(base_mem_limit, 8)
        # On prend le max entre (compte estimé) et (base) pour que le thème puisse augmenter N même si peu d'items existent.
        memories_limit = max(3, min(10, max(mem_count_est, base_mem_limit)))

        # Search: borné, un peu plus large si thème mémoire
        search_limit = 10 if not theme else (12 if theme.lower() in {"mémoire", "memory"} else 10)

        # Identity
        actions.append(
            Action(
                ActionType.CONSULT_IDENTITY,
                {
                    "_preview": identity_preview,
                    "_count_est": len(identity_preview),
                    "_hint": f"top={identity_preview[0][:40]}..." if identity_preview else "",
                },
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Traits
        actions.append(
            Action(
                ActionType.CONSULT_TRAITS,
                {
                    "limit": int(traits_limit),
                    "_preview": traits_preview,
                    "_count_est": int(trait_count_est),
                    "_hint": f"top={traits_preview[0]}" if traits_preview else "",
                },
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Environment / capabilities
        actions.append(
            Action(
                ActionType.CONSULT_ENVIRONMENT,
                {},
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Memory option
        actions.append(
            Action(
                ActionType.CONSULT_MEMORY,
                {
                    "limit": int(memories_limit),
                    "_preview": mem_preview,
                    "_count_est": int(mem_count_est),
                    "_hint": f"top={mem_preview[0][:40]}..." if mem_preview else "",
                },
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Option de recherche mémoire (toujours proposée pour l'instant)
        if not _already_done(ActionType.SEARCH_MEMORY.value):
            actions.append(
                Action(
                    ActionType.SEARCH_MEMORY,
                    {
                        "query": user_message,
                        "limit": int(search_limit),
                        "_preview": search_preview,
                        "_hint": f"top={search_preview[0][:40]}..." if search_preview else "",
                    },
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        # External option (Gemini/externe) proposée en option
        if not _already_done(ActionType.QUERY_EXTERNAL.value):
            actions.append(
                Action(
                    ActionType.QUERY_EXTERNAL,
                    {"query": user_message},
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        # Respond + back to base
        actions.append(
            Action(
                ActionType.RESPOND,
                {},
                priority=priority,
                required=True,
            )
        )
        priority += 1
        actions.append(
            Action(
                ActionType.NAVIGATE_BASE,
                {},
                priority=priority,
                required=False,
            )
        )

        filtered = self.action_filter.filter_actions(
            actions=actions,
            execution_results=execution_results,
            user_request=user_message,
        )

        # Recommandation via patterns V2 (si disponible en DB via MemoryStore)
        recommended_action: Optional[ActionType] = None
        try:
            if hasattr(self.memory_store, "get_pattern_recommendation"):
                rec = self.memory_store.get_pattern_recommendation(
                    menu_context="general",
                    prev_step=prev_step,
                    theme_pattern=theme,
                )
                if rec and rec.get("recommended_step"):
                    recommended_action = self._pattern_rec_action_type(str(rec["recommended_step"]), "general")
        except Exception:
            recommended_action = None

        return self._reorder_with_recommendation(filtered, recommended_action)

    def build_specific_menu(
        self,
        menu_type: str,  # "memories", "identity", "traits", "capabilities"
        user_message: str,
        execution_results: Dict[str, Any],
        session_id: str,
    ) -> List[Action]:
        """Construit un menu spécifique selon le type (souvenirs, traits, identité, capacités)."""
        _ = session_id

        menu_type = (menu_type or "").strip().lower()
        actions: List[Action] = []
        priority = 1

        if menu_type == "memories":
            # Sous-menu spécialisé souvenirs
            # 1) Voir N derniers souvenirs (priorisés par MemoryRank)
            mem_preview: List[str] = []
            mem_count_est = 0
            try:
                m_items = self.navigator.get_top_memories(limit=50)
                mem_count_est = len(m_items)
                mem_preview = [str(m.get("content") or "")[:80] for m in m_items[:3] if (m.get("content") or "")]
            except Exception:
                pass

            limit = max(5, min(20, mem_count_est or 10))
            actions.append(
                Action(
                    ActionType.CONSULT_MEMORIES,
                    {
                        "limit": int(limit),
                        "_preview": mem_preview,
                        "_count_est": int(mem_count_est),
                        "_hint": f"top={mem_preview[0][:40]}..." if mem_preview else "",
                    },
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

            # 2) Recherche dans souvenirs
            actions.append(
                Action(
                    ActionType.SEARCH_MEMORY,
                    {
                        "query": user_message,
                        "limit": 10,
                        "_hint": "Recherche ciblée dans les souvenirs.",
                    },
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        elif menu_type == "traits":
            # Sous-menu spécialisé traits
            traits_preview: List[str] = []
            trait_count_est = 0
            try:
                t_items = self.navigator.get_top_traits(limit=50)
                trait_count_est = len(t_items)
                traits_preview = [
                    f"{(t.get('label') or '')} (w={float(t.get('weight') or 0.0):.1f})"
                    for t in t_items[:5]
                    if t.get("label")
                ]
            except Exception:
                pass

            limit = max(5, min(30, trait_count_est or 20))
            actions.append(
                Action(
                    ActionType.CONSULT_TRAITS,
                    {
                        "limit": int(limit),
                        "_preview": traits_preview,
                        "_count_est": int(trait_count_est),
                        "_hint": f"top={traits_preview[0]}" if traits_preview else "",
                    },
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        elif menu_type == "identity":
            # Sous-menu spécialisé identité
            identity_preview: List[str] = []
            try:
                id_items = self.navigator.get_identity_phrases(limit=5)
                identity_preview = [
                    str(x.get("content") or "")[:100] for x in id_items if (x.get("content") or "")
                ]
            except Exception:
                pass

            actions.append(
                Action(
                    ActionType.CONSULT_IDENTITY,
                    {
                        "_preview": identity_preview,
                        "_count_est": len(identity_preview),
                        "_hint": f"top={identity_preview[0][:40]}..." if identity_preview else "",
                    },
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        elif menu_type == "capabilities":
            # Sous-menu spécialisé capacités/environnement (pour l'instant, un simple redirect)
            actions.append(
                Action(
                    ActionType.CONSULT_ENVIRONMENT,
                    {},
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        else:
            # Fallback : menu général
            logger.info(
                f"[MENU_BUILDER] build_specific_menu(type={menu_type}, session={session_id}) inconnu, fallback sur menu général."
            )
            return self.build_general_menu(
                user_message=user_message,
                execution_results=execution_results,
                session_id=session_id,
            )

        # Ajouter RESPOND + retour vers le menu général
        actions.append(
            Action(
                ActionType.RESPOND,
                {},
                priority=priority,
                required=True,
            )
        )
        priority += 1
        actions.append(
            Action(
                ActionType.NAVIGATE_GENERAL,
                {},
                priority=priority,
                required=False,
            )
        )

        filtered = self.action_filter.filter_actions(
            actions=actions,
            execution_results=execution_results,
            user_request=user_message,
        )
        return filtered



