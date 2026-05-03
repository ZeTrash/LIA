"""CognitivePlanner: cognitive planning primitives for LIA.

This module serves two complementary roles:

1) **Menu proposal** (recommended path, aligns with `prompt_memory_performing.md`)
   - The planner proposes a *menu* of possible next actions.
   - The *agent* (LLM) chooses which action to execute.
   - An orchestrator (e.g. `LLMAdapter`) loops: propose → choose → execute → repeat → RESPOND.

2) **Heuristic planning fallback** (safe deterministic mode)
   - The planner can still output a full `ActionPlan` directly using keyword heuristics
     and optional pattern hints.
   - Useful as a fallback, for debugging, or when you want deterministic behavior.

Important constraints that remain true for this module:
- no DB writes
- safe even if optional services are missing
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from .cognitive_models import Action, ActionPlan, ActionType, RequestAnalysis

logger = logging.getLogger(__name__)


class PatternLearnerLike(Protocol):
    """Minimal protocol for a future PatternLearner."""

    def get_preferred_patterns(self, request_type: str, context: Dict[str, Any]) -> List[Any]: ...


@dataclass(frozen=True)
class PlannerConfig:
    max_depth: int = 3
    default_memory_limit: int = 5
    default_interactions_limit: int = 5
    default_memories_limit: int = 5
    stop_words_lang: str = "fr"


class CognitivePlanner:
    """Builds an ActionPlan from a user message."""

    def __init__(
        self,
        memory_adapter: Any = None,
        pattern_learner: Optional[PatternLearnerLike] = None,
        config: Optional[PlannerConfig] = None,
        safeguards: Any = None,  # Phase 5
        optimizer: Any = None,  # Phase 5
    ):
        self.memory = memory_adapter
        self.pattern_learner = pattern_learner
        self.config = config or PlannerConfig()
        self.safeguards = safeguards  # Phase 5
        self.optimizer = optimizer  # Phase 5

        # Initialiser éventuellement un MenuBuilder (Phase menu optimal)
        self.menu_builder = None
        try:
            # Import local pour éviter les imports circulaires
            from .menu_builder import MenuBuilder

            memory_store = getattr(memory_adapter, "store", None)
            if memory_store is not None:
                self.menu_builder = MenuBuilder(
                    memory_store=memory_store,
                    pattern_learner=pattern_learner,
                    config=self.config,
                )
                logger.info("✅ [PLANNER] MenuBuilder initialisé (menus basés sur MemoryRank/Patterns).")
            else:
                logger.info("ℹ️ [PLANNER] MenuBuilder non initialisé (memory_adapter.store manquant).")
        except Exception as e:  # pragma: no cover - fail-safe
            logger.warning(f"⚠️ [PLANNER] Impossible d'initialiser MenuBuilder: {e}")

    async def plan(self, user_message: str, session_id: str = "default") -> ActionPlan:
        """Return an ActionPlan for the message.

        Phase 5: utilise garde-fous, optimisations et cache.
        """
        logger.info(f"🧠 [PLANNER] Début planification pour: '{user_message[:50]}...' (session: {session_id})")
        
        # Phase 5: Vérifier le cache d'abord
        if self.optimizer:
            logger.debug(f"🔍 [PLANNER] Vérification du cache...")
            analysis_temp = self._analyze_request(user_message)
            cached_plan = self.optimizer.get_cached_plan(user_message, analysis_temp)
            if cached_plan:
                logger.info(f"✅ [PLANNER] Plan récupéré depuis le cache ({len(cached_plan.actions)} actions)")
                return cached_plan
            logger.debug(f"🔍 [PLANNER] Aucun plan en cache")
        
        logger.debug(f"🔍 [PLANNER] Analyse de la requête...")
        analysis = self._analyze_request(user_message)
        logger.info(
            f"📊 [PLANNER] Analyse: complexité={analysis.complexity}, "
            f"needs_identity={analysis.needs_identity}, "
            f"needs_memory={analysis.needs_memory}, "
            f"needs_external={analysis.needs_external}, "
            f"keywords={analysis.keywords[:5]}"
        )
        
        # Phase 5: Vérifier les garde-fous (profondeur)
        if self.safeguards:
            current_depth = self.safeguards.get_budget(session_id).depth
            logger.debug(f"🔍 [PLANNER] Vérification profondeur: {current_depth}")
            if not self.safeguards.check_decision_depth(session_id, current_depth):
                # Créer un plan minimal en cas de limite dépassée
                logger.warning(f"⚠️  [PLANNER] Limite de profondeur atteinte ({current_depth}), plan minimal créé")
                return ActionPlan(
                    actions=[Action(ActionType.RESPOND, {}, priority=1)],
                    estimated_cost=50.0,
                    confidence=0.5
                )

        actions: List[Action] = []
        priority = 1

        # Phase 3: Consulter les patterns préférés si disponible
        preferred_pattern = None
        if self.pattern_learner:
            logger.debug(f"🔍 [PLANNER] Consultation des patterns préférés (type: {analysis.complexity})...")
            try:
                preferred_patterns = self.pattern_learner.get_preferred_patterns(
                    request_type=analysis.complexity, 
                    context={"keywords": analysis.keywords}
                )
                if preferred_patterns:
                    # Utiliser le meilleur pattern
                    preferred_pattern = preferred_patterns[0]
                    logger.info(f"✅ [PLANNER] Pattern préféré trouvé: {len(preferred_pattern.action_sequence)} actions (success_rate: {preferred_pattern.success_rate:.2f})")
                else:
                    logger.debug(f"🔍 [PLANNER] Aucun pattern préféré trouvé")
            except Exception as e:
                # Ne pas faire échouer la planification si le learner échoue
                logger.warning(f"⚠️  [PLANNER] Erreur lors de la récupération des patterns: {e}")

        # Si un pattern préféré existe, l'utiliser
        if preferred_pattern:
            logger.info(f"📋 [PLANNER] Construction du plan depuis le pattern préféré...")
            # Construire les actions depuis le pattern
            for action_type in preferred_pattern.action_sequence:
                if action_type == ActionType.CONSULT_PATTERNS:
                    # Ignorer cette action (déjà consulté)
                    continue
                elif action_type == ActionType.CONSULT_IDENTITY:
                    actions.append(Action(ActionType.CONSULT_IDENTITY, {}, priority=priority))
                    priority += 1
                elif action_type == ActionType.CONSULT_MEMORY:
                    default_limit = self.config.get("default_memory_limit", 5) if isinstance(self.config, dict) else getattr(self.config, "default_memory_limit", 5)
                    actions.append(Action(ActionType.CONSULT_MEMORY, {"limit": default_limit}, priority=priority))
                    priority += 1
                elif action_type == ActionType.CONSULT_INTERACTIONS:
                    default_limit = self.config.get("default_interactions_limit", 5) if isinstance(self.config, dict) else getattr(self.config, "default_interactions_limit", 5)
                    actions.append(Action(ActionType.CONSULT_INTERACTIONS, {"limit": default_limit}, priority=priority))
                    priority += 1
                elif action_type == ActionType.CONSULT_MEMORIES:
                    default_limit = self.config.get("default_memories_limit", 5) if isinstance(self.config, dict) else getattr(self.config, "default_memories_limit", 5)
                    actions.append(Action(ActionType.CONSULT_MEMORIES, {"limit": default_limit}, priority=priority))
                    priority += 1
                elif action_type == ActionType.QUERY_EXTERNAL:
                    actions.append(Action(ActionType.QUERY_EXTERNAL, {"query": user_message, "keywords": analysis.keywords}, priority=priority, required=False))
                    priority += 1
                elif action_type == ActionType.RESPOND:
                    # Toujours ajouter RESPOND en dernier
                    pass
            
            # Si le pattern ne contient pas RESPOND, l'ajouter
            if not any(a.type == ActionType.RESPOND for a in actions):
                actions.append(Action(ActionType.RESPOND, {}, priority=priority))
        else:
            logger.info(f"📋 [PLANNER] Construction du plan depuis les heuristiques...")
            # Pas de pattern préféré, utiliser les heuristiques
            # 0) Patterns (optional debug): only if learner exists
            # Note: le planner consulte déjà les patterns pour choisir un plan; cette action sert uniquement
            # à tracer / inspecter côté exécuteur si besoin.
            if self.pattern_learner:
                actions.append(
                    Action(
                        ActionType.CONSULT_PATTERNS,
                        {"request_type": analysis.complexity, "context": {"keywords": analysis.keywords}},
                        priority=priority,
                        required=False,
                    )
                )
                priority += 1
                logger.debug(f"  ➕ Action ajoutée: CONSULT_PATTERNS (priority: {priority-1})")

            # 1) Identity
            if analysis.needs_identity:
                actions.append(Action(ActionType.CONSULT_IDENTITY, {}, priority=priority))
                priority += 1
                logger.debug(f"  ➕ Action ajoutée: CONSULT_IDENTITY (priority: {priority-1})")

            # 2) Memory related
            if analysis.needs_memory:
                logger.debug(f"  ➕ Actions mémoire ajoutées...")
                # Prefer interactions first (conversation), then memories
                default_limit = self.config.get("default_interactions_limit", 5) if isinstance(self.config, dict) else getattr(self.config, "default_interactions_limit", 5)
                actions.append(
                    Action(
                        ActionType.CONSULT_INTERACTIONS,
                        {"limit": default_limit},
                        priority=priority,
                    )
                )
                priority += 1
                default_memories_limit = self.config.get("default_memories_limit", 5) if isinstance(self.config, dict) else getattr(self.config, "default_memories_limit", 5)
                actions.append(
                    Action(
                        ActionType.CONSULT_MEMORIES,
                        {"limit": default_memories_limit},
                        priority=priority,
                    )
                )
                priority += 1

            # 3) External query (Gemini) only if user asks for fresh info / research-like intent
            if analysis.needs_external:
                actions.append(
                    Action(
                        ActionType.QUERY_EXTERNAL,
                        {"query": user_message, "keywords": analysis.keywords},
                        priority=priority,
                        required=False,
                    )
                )
                priority += 1
                logger.debug(f"  ➕ Action ajoutée: QUERY_EXTERNAL (priority: {priority-1})")

            # 4) Always respond
            actions.append(Action(ActionType.RESPOND, {}, priority=priority))
            logger.debug(f"  ➕ Action ajoutée: RESPOND (priority: {priority})")

        # Enforcer: même si un pattern est choisi, on ne doit pas ignorer les besoins détectés
        # (ex: "Qui es-tu ?" doit inclure CONSULT_IDENTITY).
        def _has_action(t: ActionType) -> bool:
            return any(a.type == t for a in actions)

        # Retirer RESPOND temporairement pour insérer les actions manquantes avant la réponse.
        respond_action = None
        non_respond_actions: List[Action] = []
        for a in sorted(actions, key=lambda x: x.priority):
            if a.type == ActionType.RESPOND:
                respond_action = a
            else:
                non_respond_actions.append(a)

        # 1) Identity required by analysis
        if analysis.needs_identity and not any(a.type == ActionType.CONSULT_IDENTITY for a in non_respond_actions):
            logger.info("🔧 [PLANNER] Ajout CONSULT_IDENTITY (besoin détecté, absent du pattern)")
            non_respond_actions.append(Action(ActionType.CONSULT_IDENTITY, {}, priority=0))

        # 2) Memory required by analysis
        if analysis.needs_memory and not any(
            a.type in (ActionType.CONSULT_MEMORY, ActionType.CONSULT_INTERACTIONS, ActionType.CONSULT_MEMORIES)
            for a in non_respond_actions
        ):
            logger.info("🔧 [PLANNER] Ajout actions mémoire (besoin détecté, absent du pattern)")
            default_limit = (
                self.config.get("default_interactions_limit", 5)
                if isinstance(self.config, dict)
                else getattr(self.config, "default_interactions_limit", 5)
            )
            non_respond_actions.append(
                Action(ActionType.CONSULT_INTERACTIONS, {"limit": default_limit}, priority=0)
            )
            default_memories_limit = (
                self.config.get("default_memories_limit", 5)
                if isinstance(self.config, dict)
                else getattr(self.config, "default_memories_limit", 5)
            )
            non_respond_actions.append(
                Action(ActionType.CONSULT_MEMORIES, {"limit": default_memories_limit}, priority=0)
            )

        # 3) External required by analysis
        if analysis.needs_external and not any(a.type == ActionType.QUERY_EXTERNAL for a in non_respond_actions):
            logger.info("🔧 [PLANNER] Ajout QUERY_EXTERNAL (besoin détecté, absent du pattern)")
            non_respond_actions.append(
                Action(
                    ActionType.QUERY_EXTERNAL,
                    {"query": user_message, "keywords": analysis.keywords},
                    priority=0,
                    required=False,
                )
            )

        # Re-normaliser les priorités (dataclasses frozen=True → recréer les Actions)
        normalized: List[Action] = []
        next_priority = 1
        for a in non_respond_actions:
            normalized.append(
                Action(
                    a.type,
                    dict(a.parameters) if isinstance(a.parameters, dict) else {},
                    priority=next_priority,
                    required=a.required,
                )
            )
            next_priority += 1

        # Toujours RESPOND en dernier
        normalized.append(Action(ActionType.RESPOND, {}, priority=next_priority))
        actions = normalized

        estimated_cost = self._estimate_cost(actions)
        confidence = self._estimate_confidence(analysis, actions)
        
        logger.info(f"📊 [PLANNER] Plan créé: {len(actions)} actions, coût={estimated_cost:.1f}, confiance={confidence:.2f}")
        
        plan = ActionPlan(actions=actions, estimated_cost=estimated_cost, confidence=confidence)
        
        # Phase 5: Valider le plan avec les garde-fous
        if self.safeguards:
            logger.debug(f"🔍 [PLANNER] Validation du plan par les garde-fous...")
            is_valid, issues = self.safeguards.validate_plan(session_id, plan, user_message=user_message)
            if not is_valid:
                logger.warning(f"⚠️  [PLANNER] Plan invalidé par garde-fous: {issues}")
                # Créer un plan minimal mais intelligent en cas d'invalidation
                # Essayer de garder au moins les actions nécessaires basées sur l'analyse
                logger.info(f"🔧 [PLANNER] Création d'un plan minimal intelligent...")
                minimal_actions = []
                priority = 1
                if analysis.needs_identity:
                    minimal_actions.append(Action(ActionType.CONSULT_IDENTITY, {}, priority=priority))
                    priority += 1
                    logger.debug(f"  ➕ Action minimale: CONSULT_IDENTITY")
                if analysis.needs_external:
                    minimal_actions.append(Action(ActionType.QUERY_EXTERNAL, {"query": user_message, "keywords": analysis.keywords}, priority=priority, required=False))
                    priority += 1
                    logger.debug(f"  ➕ Action minimale: QUERY_EXTERNAL")
                # Toujours ajouter RESPOND
                minimal_actions.append(Action(ActionType.RESPOND, {}, priority=priority))
                plan = ActionPlan(
                    actions=minimal_actions,
                    estimated_cost=self._estimate_cost(minimal_actions),
                    confidence=0.4  # Légèrement meilleur que 0.3
                )
                logger.info(f"✅ [PLANNER] Plan minimal créé: {len(minimal_actions)} actions")
        
        # Phase 5: Mettre en cache le plan
        if self.optimizer:
            logger.debug(f"💾 [PLANNER] Mise en cache du plan...")
            self.optimizer.cache_plan(user_message, analysis, plan)
        
        logger.info(f"✅ [PLANNER] Planification terminée: {len(plan.actions)} actions finales")
        return plan

    def build_action_menu(
        self,
        user_message: str,
        execution_results: Optional[Dict[str, Any]] = None,
        session_id: str = "default",
    ) -> List[Action]:
        """
        Build a *menu* of possible next actions based on the request analysis and what
        has already been executed.

        This is meant for a "menu -> agent chooses -> execute -> repeat" cognitive loop
        implemented by a higher-level orchestrator (e.g. `LLMAdapter`).

        The planner remains deterministic here: it proposes options, it does not choose.
        """
        _ = session_id
        execution_results = execution_results or {}
        analysis = self._analyze_request(user_message)

        menu: List[Action] = []
        priority = 1

        def _already_done(action_value: str) -> bool:
            return action_value in execution_results

        # Menu state is stored by the executor into execution_results["_menu_state"].
        state = str(execution_results.get("_menu_state") or "base")

        # Si un MenuBuilder est disponible, l'utiliser en priorité.
        if self.menu_builder is not None:
            try:
                if state == "base":
                    return self.menu_builder.build_base_menu(
                        user_message=user_message,
                        execution_results=execution_results,
                        session_id=session_id,
                    )
                elif state == "general":
                    return self.menu_builder.build_general_menu(
                        user_message=user_message,
                        execution_results=execution_results,
                        session_id=session_id,
                    )
                elif state.startswith("specific:"):
                    menu_type = state.split(":", 1)[1]
                    return self.menu_builder.build_specific_menu(
                        menu_type=menu_type,
                        user_message=user_message,
                        execution_results=execution_results,
                        session_id=session_id,
                    )
            except Exception as e:  # pragma: no cover - fail-safe
                logger.warning(f"⚠️ [PLANNER] Erreur dans MenuBuilder, fallback sur menu heuristique: {e}")

        # --- Fallback heuristique (comportement historique) ---
        if state == "base":
            # 1) Patterns (optional)
            # NOTE: patterns consultés via LLMAdapter, section recommandation.

            # 2) Voir la demande utilisateur (toujours possible, sans l'inclure dans le prompt du menu)
            if not _already_done(ActionType.CONSULT_REQUEST.value):
                menu.append(
                    Action(
                        ActionType.CONSULT_REQUEST,
                        {"request": user_message},
                        priority=priority,
                        required=False,
                    )
                )
                priority += 1

            # 3) Aller au menu général (mémoire / identité / traits / environnement)
            menu.append(
                Action(
                    ActionType.NAVIGATE_GENERAL,
                    {},
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

            # 4) Toujours permettre de répondre
            menu.append(
                Action(
                    ActionType.RESPOND,
                    {},
                    priority=priority,
                    required=True,
                )
            )
            return menu

        # --- GENERAL MENU (after NAVIGATE_GENERAL) ---
        # Identity (toujours proposée, même si déjà consultée - l'agent peut vouloir la revoir)
        menu.append(
            Action(
                ActionType.CONSULT_IDENTITY,
                {},
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Traits (toujours proposée, même si déjà consultée)
        menu.append(
            Action(
                ActionType.CONSULT_TRAITS,
                {"limit": 20},
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Environment / capabilities (toujours proposée, même si déjà consultée)
        menu.append(
            Action(
                ActionType.CONSULT_ENVIRONMENT,
                {},
                priority=priority,
                required=False,
            )
        )
        priority += 1

        # Memory option (toujours proposée, même si déjà consultée)
        # On utilise CONSULT_MEMORY qui combine interactions + memories
        default_limit = (
            self.config.get("default_memory_limit", 5)
            if isinstance(self.config, dict)
            else getattr(self.config, "default_memory_limit", 5)
        )
        menu.append(
            Action(
                ActionType.CONSULT_MEMORY,
                {"limit": default_limit},
                priority=priority,
                required=False,
            )
        )
        priority += 1

        if analysis.keywords and not _already_done(ActionType.SEARCH_MEMORY.value):
            menu.append(
                Action(
                    ActionType.SEARCH_MEMORY,
                    {"query": " ".join(analysis.keywords), "limit": 10},
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        # External option (Gemini)
        if analysis.needs_external and not _already_done(ActionType.QUERY_EXTERNAL.value):
            menu.append(
                Action(
                    ActionType.QUERY_EXTERNAL,
                    {"query": user_message, "keywords": analysis.keywords},
                    priority=priority,
                    required=False,
                )
            )
            priority += 1

        # Respond + back to base
        menu.append(
            Action(
                ActionType.RESPOND,
                {},
                priority=priority,
                required=True,
            )
        )
        priority += 1
        menu.append(
            Action(
                ActionType.NAVIGATE_BASE,
                {},
                priority=priority,
                required=False,
            )
        )
        return menu

    def _estimate_cost(self, actions: List[Action]) -> float:
        cost = 0.0
        for a in actions:
            if a.type == ActionType.RESPOND:
                cost += 50.0
            elif a.type in (ActionType.CONSULT_INTERACTIONS, ActionType.CONSULT_MEMORIES, ActionType.CONSULT_MEMORY):
                cost += 20.0
            elif a.type == ActionType.QUERY_EXTERNAL:
                cost += 40.0
            else:
                cost += 10.0
        return cost

    def _estimate_confidence(self, analysis: RequestAnalysis, actions: List[Action]) -> float:
        # Conservative baseline; bump if we included actions that match detected needs.
        score = 0.55
        if analysis.needs_identity and any(a.type == ActionType.CONSULT_IDENTITY for a in actions):
            score += 0.15
        if analysis.needs_memory and any(a.type in (ActionType.CONSULT_INTERACTIONS, ActionType.CONSULT_MEMORIES) for a in actions):
            score += 0.15
        if analysis.needs_external and any(a.type == ActionType.QUERY_EXTERNAL for a in actions):
            score += 0.10
        return max(0.0, min(1.0, score))

    def _analyze_request(self, message: str) -> RequestAnalysis:
        msg = message.lower().strip()

        # Identity intents (French + common English)
        needs_identity = any(
            k in msg
            for k in (
                "qui es-tu",
                "qui es tu",
                "qui est-tu",
                "qui est tu",
                "ton nom",
                "ton identité",
                "ton identite",
                "qui suis-je",
                "qui suis je",
                "t'es qui",
                "who are you",
                "your name",
                "your identity",
            )
        )

        # Memory intents
        needs_memory = any(
            k in msg
            for k in (
                "souvenir",
                "souviens",
                "rappelle",
                "mémoire",
                "memoire",
                "avant",
                "précédent",
                "precedent",
                "hier",
                "la dernière fois",
                "derniere fois",
                "notre conversation",
                "notre discussion",
            )
        )

        # External info intents
        needs_external = any(
            k in msg
            for k in (
                "cherche",
                "recherche",
                "source",
                "référence",
                "reference",
                "lien",
                "actualités",
                "actualites",
                "aujourd'hui",
                "today",
                "latest",
                "à jour",
                "a jour",
                "gemini",  # Demande d'utiliser Gemini
                "consulter",  # Demande de consulter une source externe
                "consulte",  # Variante
                "demande à",  # Demande de poser une question à une source externe
                "demande",  # Variante
                "interroge",  # Demande d'interroger une source
                "interroger",  # Variante
                "qu'est ce que",  # Questions de définition (souvent besoin externe)
                "qu'est-ce que",  # Variante
                "c'est quoi",  # Questions de définition
                "qu'est",  # Questions de définition
            )
        )

        complexity = "simple"
        if (needs_memory and needs_external) or (needs_identity and needs_external):
            complexity = "complex"
        elif needs_memory or needs_external:
            complexity = "moderate"

        keywords = self._extract_keywords(message)
        return RequestAnalysis(
            complexity=complexity,
            needs_memory=needs_memory,
            needs_identity=needs_identity,
            needs_external=needs_external,
            keywords=keywords,
        )

    def _extract_keywords(self, text: str) -> List[str]:
        # Tokenize words, keep basic letters/numbers, strip punctuation.
        tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+", text.lower())

        # Config peut être un dict ou un objet
        stop_words_lang = self.config.get("stop_words_lang", "fr") if isinstance(self.config, dict) else getattr(self.config, "stop_words_lang", "fr")
        
        if stop_words_lang == "fr":
            stop = {
                "le",
                "la",
                "les",
                "un",
                "une",
                "des",
                "de",
                "du",
                "et",
                "ou",
                "mais",
                "pour",
                "avec",
                "sans",
                "sur",
                "dans",
                "par",
                "est",
                "sont",
                "être",
                "etre",
                "avoir",
                "faire",
                "peux",
                "peut",
                "veux",
                "veut",
                "tu",
                "je",
                "il",
                "elle",
                "nous",
                "vous",
                "ils",
                "elles",
                "qui",
                "que",
                "quoi",
                "où",
                "ou",
                "comment",
                "pourquoi",
                "quand",
                "comme",
                "très",
                "tres",
                "plus",
                "moins",
            }
        else:
            stop = set()

        keywords = [t for t in tokens if len(t) > 3 and t not in stop]
        # Keep order, de-duplicate
        seen = set()
        out: List[str] = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                out.append(k)
        return out[:5]



