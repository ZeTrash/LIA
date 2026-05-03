"""PatternLearner: apprend et optimise les patterns d'exécution (Phase 3).

Le PatternLearner enregistre les suites d'actions exécutées, évalue leur efficacité,
et maintient une base de patterns préférés pour guider les décisions futures.
"""

from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cognitive_models import (
    ActionPlan,
    ActionType,
    ExecutionResult,
    Pattern,
    RequestAnalysis,
    VerificationResult,
)

logger = logging.getLogger(__name__)


class PatternLearner:
    """Apprenant de patterns pour optimiser les décisions cognitives."""

    def __init__(
        self,
        memory_adapter=None,
        config: Optional[Dict[str, Any]] = None,
        storage_path: Optional[str] = None,
    ):
        """
        Initialise l'apprenant de patterns.

        Args:
            memory_adapter: Adaptateur mémoire (optionnel, pour stockage futur)
            config: Configuration
            storage_path: Chemin pour stocker les patterns (défaut: data/patterns.json)
        """
        self.memory = memory_adapter
        self.config = config or {}
        
        # Chemin de stockage
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Par défaut, stocker dans data/patterns.json
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            self.storage_path = data_dir / "patterns.json"
        
        # Patterns en mémoire
        self.patterns: Dict[str, Pattern] = {}

        # Meta (non lié à un pattern unique): politiques/hints appris.
        # Ex: budget d'itérations recommandé par type de requête.
        # Format (version >= 1.1):
        # {
        #   "iteration_policy": {
        #       "simple": {"history_steps": [1,2,1,...], "last_updated": "..."},
        #       "moderate": {...},
        #   }
        # }
        self.meta: Dict[str, Any] = {"iteration_policy": {}}
        
        # Configuration
        self.min_success_rate = self.config.get("min_success_rate", 0.7)
        self.min_usage_count = self.config.get("min_usage_count", 5)
        self.update_interval_hours = self.config.get("update_interval_hours", 24)
        
        # Charger les patterns existants
        self._load_patterns()
        
        logger.info(f"PatternLearner initialisé avec {len(self.patterns)} patterns")

    def get_preferred_patterns(
        self,
        request_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Pattern]:
        """
        Retourne les patterns préférés pour un type de requête.

        Args:
            request_type: Type de requête ("simple", "moderate", "complex")
            context: Contexte additionnel (optionnel)

        Returns:
            Liste des patterns préférés, triés par efficacité
        """
        if not self.patterns:
            return []

        # Filtrer les patterns pertinents
        relevant_patterns = []
        for pattern in self.patterns.values():
            # Vérifier si le pattern correspond au type de requête
            if request_type in pattern.request_types or not pattern.request_types:
                # Vérifier les critères minimaux
                if (
                    pattern.success_rate >= self.min_success_rate
                    and pattern.usage_count >= self.min_usage_count
                ):
                    relevant_patterns.append(pattern)

        # Trier par efficacité (score composite)
        relevant_patterns.sort(
            key=lambda p: self._calculate_efficiency_score(p), reverse=True
        )

        # Retourner les top patterns (max 5)
        result = relevant_patterns[:5]
        logger.info(f"✅ [PATTERN_LEARNER] {len(result)} patterns préférés trouvés pour type: {request_type}")
        return result

    def record_execution(
        self,
        plan: ActionPlan,
        execution_result: ExecutionResult,
        verification_result: Optional[VerificationResult] = None,
        request_analysis: Optional[RequestAnalysis] = None,
        user_feedback: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Enregistre l'exécution d'un plan pour apprentissage.

        Args:
            plan: Plan d'actions exécuté
            execution_result: Résultat de l'exécution
            verification_result: Résultat de la vérification (optionnel)
            request_analysis: Analyse de la requête (optionnel)
            user_feedback: Feedback utilisateur (optionnel)
        """
        logger.debug(f"📚 [PATTERN_LEARNER] Enregistrement de l'exécution: {len(plan.actions)} actions")
        if not execution_result.success:
            # Ne pas apprendre des patterns qui échouent
            logger.debug(f"  ⚠️  [PATTERN_LEARNER] Exécution échouée, pattern non enregistré")
            return

        # Extraire la séquence d'actions
        action_sequence = [action.type for action in plan.sorted_actions()]

        # Mettre à jour les hints de politique d'itérations (menu loop)
        try:
            request_type = (request_analysis.complexity if request_analysis else "unknown") or "unknown"
            steps = max(0, len(action_sequence) - 1)  # exclure RESPOND
            is_good = bool(execution_result.success) and bool(getattr(verification_result, "is_valid", True))
            quality = float(getattr(verification_result, "overall_score", 0.0) or 0.0) if verification_result else 0.0
            logger.info(
                f"🧠 [PATTERN_LEARNER] Iteration policy observation: request_type={request_type}, "
                f"steps={steps}, is_good={is_good}, quality={quality:.2f}"
            )
            self.record_iteration_observation(request_type=request_type, steps=steps, is_good=is_good, quality=quality)
        except Exception as e:
            logger.debug(f"  ⚠️  [PATTERN_LEARNER] Impossible d'enregistrer la politique d'itérations: {e}")

        # Créer une clé unique pour le pattern (basée sur la séquence)
        pattern_key = self._generate_pattern_key(action_sequence)

        # Récupérer ou créer le pattern
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
        else:
            # Créer un nouveau pattern
            pattern = Pattern(
                id=pattern_key,
                action_sequence=action_sequence,
                request_types=[],
                success_rate=0.0,
                avg_quality_score=0.0,
                avg_execution_time=0.0,
                usage_count=0,
                last_used=None,
            )
            self.patterns[pattern_key] = pattern

        # Mettre à jour le pattern
        logger.debug(f"  🔄 [PATTERN_LEARNER] Mise à jour du pattern: {pattern_key}")
        self._update_pattern(
            pattern,
            execution_result,
            verification_result,
            request_analysis,
            user_feedback,
        )
        logger.info(f"  ✅ [PATTERN_LEARNER] Pattern mis à jour: success_rate={pattern.success_rate:.2f}, usage_count={pattern.usage_count}")

        # Sauvegarder périodiquement
        self._save_patterns()

    def record_iteration_observation(
        self,
        request_type: str,
        steps: int,
        is_good: bool = True,
        quality: float = 0.0,
        max_history: int = 30,
    ) -> None:
        """
        Enregistre une observation du nombre d'étapes internes (actions non-RESPOND)
        utilisées pour résoudre une requête.

        Objectif: laisser le système apprendre un budget d'itérations recommandé
        par type de requête, sans hardcode/config statique.
        """
        request_type = (request_type or "unknown").strip() or "unknown"
        steps = int(max(0, steps))

        # Par défaut, ne retenir que les exécutions "bonnes".
        # Qualité peut aussi servir de filtre léger (>= 0.5) si disponible.
        if not is_good:
            logger.debug(
                f"🧠 [PATTERN_LEARNER] Iteration policy skipped (not good): request_type={request_type}, steps={steps}"
            )
            return
        if quality and quality < 0.5:
            logger.debug(
                f"🧠 [PATTERN_LEARNER] Iteration policy skipped (low quality={quality:.2f}): "
                f"request_type={request_type}, steps={steps}"
            )
            return

        policy = self.meta.setdefault("iteration_policy", {})
        bucket = policy.setdefault(request_type, {"history_steps": [], "last_updated": None})
        history: List[int] = bucket.setdefault("history_steps", [])
        history.append(steps)

        # Tronquer historique
        if len(history) > max_history:
            bucket["history_steps"] = history[-max_history:]

        bucket["last_updated"] = datetime.now(UTC).isoformat()
        logger.info(
            f"🧠 [PATTERN_LEARNER] Iteration policy stored: request_type={request_type}, "
            f"steps={steps}, history_size={len(bucket.get('history_steps') or [])}"
        )

    def recommend_max_iterations(
        self,
        request_type: str,
        hard_limit: int,
        default: int = 6,
        min_value: int = 1,
    ) -> int:
        """
        Recommande un max_iterations (nombre d'itérations menu) à partir des observations apprises.

        - Toujours borné par `hard_limit` (garde-fous anti-boucle).
        - Si peu/pas de données, retourne `default`.
        """
        request_type = (request_type or "unknown").strip() or "unknown"
        hard_limit = int(max(1, hard_limit))
        default = int(max(min_value, default))

        policy = (self.meta or {}).get("iteration_policy", {}) or {}
        bucket = policy.get(request_type) or {}
        history = bucket.get("history_steps") or []

        if not history:
            recommended = min(hard_limit, default)
            logger.info(
                f"🧠 [PATTERN_LEARNER] Iteration policy recommend: request_type={request_type}, "
                f"history=empty, default={default}, hard_limit={hard_limit} -> {recommended}"
            )
            return recommended

        # Median is robust to outliers.
        try:
            med = int(round(statistics.median([int(x) for x in history if int(x) >= 0])))
        except Exception:
            med = default

        # Heuristic padding: allow +1 over typical median to reduce truncation risk.
        recommended = max(min_value, med + 1)
        final = min(hard_limit, max(min_value, recommended))
        logger.info(
            f"🧠 [PATTERN_LEARNER] Iteration policy recommend: request_type={request_type}, "
            f"history_size={len(history)}, median_steps={med}, padded={recommended}, "
            f"hard_limit={hard_limit} -> {final}"
        )
        return final

    def _generate_pattern_key(self, action_sequence: List[ActionType]) -> str:
        """Génère une clé unique pour un pattern basée sur sa séquence d'actions."""
        # Utiliser la séquence d'actions comme clé
        sequence_str = "->".join([a.value for a in action_sequence])
        # Créer un hash simple pour la clé
        import hashlib

        return hashlib.md5(sequence_str.encode()).hexdigest()[:12]

    def _update_pattern(
        self,
        pattern: Pattern,
        execution_result: ExecutionResult,
        verification_result: Optional[VerificationResult],
        request_analysis: Optional[RequestAnalysis],
        user_feedback: Optional[Dict[str, Any]],
    ) -> None:
        """Met à jour un pattern avec les résultats d'une exécution."""
        # Mettre à jour le compteur d'utilisation
        pattern.usage_count += 1
        pattern.last_used = datetime.now(UTC)

        # Mettre à jour le type de requête si fourni
        if request_analysis:
            request_type = request_analysis.complexity
            if request_type not in pattern.request_types:
                pattern.request_types.append(request_type)

        # Mettre à jour le taux de succès
        # (pour l'instant, on considère que si execution_result.success, c'est un succès)
        if pattern.usage_count == 1:
            # Première utilisation
            pattern.success_rate = 1.0 if execution_result.success else 0.0
        else:
            # Mise à jour incrémentale
            old_success_count = pattern.success_rate * (pattern.usage_count - 1)
            new_success_count = old_success_count + (1.0 if execution_result.success else 0.0)
            pattern.success_rate = new_success_count / pattern.usage_count

        # Mettre à jour le score de qualité moyen
        if verification_result:
            quality_score = verification_result.overall_score
            if pattern.usage_count == 1:
                pattern.avg_quality_score = quality_score
            else:
                total_quality = pattern.avg_quality_score * (pattern.usage_count - 1)
                total_quality += quality_score
                pattern.avg_quality_score = total_quality / pattern.usage_count

        # Mettre à jour le temps d'exécution moyen
        exec_time = execution_result.execution_time
        if pattern.usage_count == 1:
            pattern.avg_execution_time = exec_time
        else:
            total_time = pattern.avg_execution_time * (pattern.usage_count - 1)
            total_time += exec_time
            pattern.avg_execution_time = total_time / pattern.usage_count

    def _calculate_efficiency_score(self, pattern: Pattern) -> float:
        """
        Calcule un score d'efficacité composite pour un pattern.

        Le score combine:
        - Taux de succès (poids: 0.4)
        - Score de qualité moyen (poids: 0.4)
        - Efficacité temporelle (poids: 0.2, inverse du temps)
        """
        # Score de succès (0.0 - 1.0)
        success_score = pattern.success_rate

        # Score de qualité (0.0 - 1.0)
        quality_score = pattern.avg_quality_score

        # Score temporel (plus rapide = meilleur, normalisé sur 0-5 secondes)
        time_score = max(0.0, min(1.0, 1.0 - (pattern.avg_execution_time / 5.0)))

        # Score composite (s'assurer que chaque composant est dans [0, 1])
        success_score = min(1.0, max(0.0, success_score))
        quality_score = min(1.0, max(0.0, quality_score))
        time_score = min(1.0, max(0.0, time_score))
        
        efficiency = (
            success_score * 0.4 + quality_score * 0.4 + time_score * 0.2
        )

        return min(1.0, max(0.0, efficiency))  # S'assurer que le résultat est dans [0, 1]

    def _load_patterns(self) -> None:
        """Charge les patterns depuis le fichier de stockage."""
        if not self.storage_path.exists():
            logger.debug(f"Fichier de patterns n'existe pas: {self.storage_path}")
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Meta (backward compatible)
            meta = data.get("meta")
            if isinstance(meta, dict):
                self.meta = meta

            for pattern_data in data.get("patterns", []):
                try:
                    pattern = Pattern.from_dict(pattern_data)
                    self.patterns[pattern.id] = pattern
                except Exception as e:
                    logger.warning(f"Erreur lors du chargement d'un pattern: {e}")

            logger.info(f"✅ {len(self.patterns)} patterns chargés depuis {self.storage_path}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des patterns: {e}")

    def _save_patterns(self) -> None:
        """Sauvegarde les patterns dans le fichier de stockage."""
        try:
            # Créer le répertoire si nécessaire
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Convertir les patterns en dictionnaires
            patterns_data = [pattern.to_dict() for pattern in self.patterns.values()]

            data = {
                "version": "1.1",
                "last_updated": datetime.now(UTC).isoformat(),
                "patterns": patterns_data,
                "meta": self.meta,
            }

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"✅ {len(self.patterns)} patterns sauvegardés")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des patterns: {e}")

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur les patterns."""
        if not self.patterns:
            return {
                "total_patterns": 0,
                "preferred_patterns": 0,
                "avg_success_rate": 0.0,
                "avg_quality_score": 0.0,
            }

        preferred = [
            p
            for p in self.patterns.values()
            if p.success_rate >= self.min_success_rate
            and p.usage_count >= self.min_usage_count
        ]

        avg_success = (
            sum(p.success_rate for p in self.patterns.values())
            / len(self.patterns)
            if self.patterns
            else 0.0
        )
        avg_quality = (
            sum(p.avg_quality_score for p in self.patterns.values())
            / len(self.patterns)
            if self.patterns
            else 0.0
        )

        return {
            "total_patterns": len(self.patterns),
            "preferred_patterns": len(preferred),
            "avg_success_rate": avg_success,
            "avg_quality_score": avg_quality,
        }

