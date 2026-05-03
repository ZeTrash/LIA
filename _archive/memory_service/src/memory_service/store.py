"""Stockage et logique métier du service mémoire."""

from __future__ import annotations

import hashlib
import json
import math
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta, UTC
from typing import Deque, Dict, Iterable, List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from . import metrics
from .config import Settings
from .models import (
    ExperienceModel,
    GovernanceParamModel,
    IndicatorModel,
    InteractionModel,
    PersonalGoalModel,
    RequestAuditModel,
    SessionGoalModel,
    SouvenirLinkModel,
    SouvenirModel,
    TraitModel,
    TraitVersionModel,
)
from .schemas import (
    ContextResponse,
    GovernanceCheckRequest,
    GovernanceCheckResponse,
    GovernanceIssue,
    InteractionLog,
    InteractionRequest,
    InteractionScores,
    MetricSnapshot,
    MetricsResponse,
    PersonalGoal,
    PersonalGoalCreate,
    PersonalGoalUpdate,
    SessionGoal,
    Souvenir,
    Trait,
    TraitUpdateRequest,
    TraitUpdateResponse,
)


class MemoryStore:
    """Implémentation persistante adossée à SQLite."""

    def __init__(self, settings: Settings, session_factory: sessionmaker):
        self.settings = settings
        self.session_factory = session_factory
        self._context_latency_samples: Deque[float] = deque(maxlen=settings.indicators_window)
        self._context_payload_samples: Deque[int] = deque(maxlen=settings.indicators_window)
        self._coherence_samples: Deque[float] = deque(maxlen=settings.indicators_window)
        self._drift_alerts: int = 0
        self._ttl_purged: int = 0
        self._ttl_total: int = 0
        self._lock = threading.RLock()

        self._bootstrap_defaults()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_context(self, session_id: str, max_memories: int | None = None) -> ContextResponse:
        start = datetime.now(UTC)
        with self._lock, self.session_factory() as session:
            self._purge_expired(session)
            traits = [
                self._to_trait(trait)
                for trait in session.scalars(select(TraitModel).where(TraitModel.status == "active")).all()
            ]
            goals = [
                self._to_session_goal(goal)
                for goal in session.scalars(select(SessionGoalModel).where(SessionGoalModel.session_id == session_id)).all()
            ]
            if not goals:
                goals = [
                    self._to_session_goal(goal)
                    for goal in session.scalars(select(SessionGoalModel).where(SessionGoalModel.session_id == "default")).all()
                ]
            memories = self._select_memories(session, max_memories)

        payload = {
            "traits": [trait.model_dump(mode="json") for trait in traits],
            "session_goals": [goal.model_dump(mode="json") for goal in goals],
            "memories": [memory.model_dump(mode="json") for memory in memories],
        }
        payload_bytes = len(json.dumps(payload).encode("utf-8"))
        checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        with self._lock:
            self._context_latency_samples.append(duration_ms)
            self._context_payload_samples.append(payload_bytes)

        metrics.CONTEXT_LATENCY_MS.observe(duration_ms)
        metrics.CONTEXT_PAYLOAD_BYTES.observe(payload_bytes)
        indicators = self._build_indicators()
        governance_metadata = {
            "context_version": datetime.now(UTC).strftime("%Y%m%d%H%M%S"),
            "build_time_ms": str(duration_ms),
            "payload_bytes": str(payload_bytes),
        }

        return ContextResponse(
            traits=traits,
            session_goals=goals,
            memories=memories,
            indicators=indicators,
            governance_metadata=governance_metadata,
            build_time_ms=duration_ms,
            trace_id=str(uuid.uuid4()),
            cache_hit=False,
            context_checksum=checksum,
        )

    def log_interaction(self, request: InteractionRequest) -> InteractionLog:
        with self._lock, self.session_factory() as session:
            existing = session.get(InteractionModel, request.interaction_id)
            if existing:
                return self._to_interaction(existing)

            raw_size = len(request.prompt.encode("utf-8")) + len(request.response.encode("utf-8"))
            severity = "error" if any("error" in a.lower() for a in request.anomalies) else "warning" if request.anomalies else "info"

            log_model = InteractionModel(
                interaction_id=request.interaction_id,
                session_id=request.session_id,
                occurred_at=datetime.now(UTC),
                prompt=request.prompt,
                response=request.response,
                scores=request.scores.model_dump(),
                derived_traits=list(request.decisions.derived_traits),
                anomalies=list(request.anomalies),
                severity=severity,
                raw_size_bytes=raw_size,
            )
            session.add(log_model)

            if request.decisions.create_memory:
                souvenir = self._souvenir_from_interaction(log_model, request)
                session.add(souvenir)

            session.commit()
            coherence = request.scores.coherence
            self._coherence_samples.append(coherence)
            session.refresh(log_model)
            metrics.INTERACTIONS_TOTAL.inc()
            return self._to_interaction(log_model)

    def update_trait(self, request: TraitUpdateRequest) -> TraitUpdateResponse:
        with self._lock, self.session_factory() as session:
            trait_model = session.get(TraitModel, request.trait_id)
            if trait_model and request.expected_version and trait_model.version != request.expected_version:
                return TraitUpdateResponse(trait=self._to_trait(trait_model), review_required=True)

            if trait_model:
                trait_model.version += 1
                # Appliquer le delta (objet) au value
                if isinstance(request.delta, dict):
                    # Logique simplifiée : merge des clés du delta
                    if "value" in request.delta:
                        trait_model.value = request.delta["value"]
                    if "weight" in request.delta:
                        trait_model.weight = request.delta["weight"]
                    if "confidence" in request.delta:
                        trait_model.confidence = request.delta["confidence"]
                trait_model.confidence = min(1.0, trait_model.confidence + 0.05)
                trait_model.last_update = datetime.now(UTC)
                trait_model.origin = request.source
                trait_model.status = "active"
                # Calculer checksum SHA3-256
                import hashlib
                trait_model.checksum = hashlib.sha3_256(trait_model.value.encode("utf-8")).hexdigest()
            else:
                initial_value = request.delta.get("value", str(request.delta)) if isinstance(request.delta, dict) else str(request.delta)
                trait_model = TraitModel(
                    trait_id=request.trait_id,
                    type=request.delta.get("type", "custom") if isinstance(request.delta, dict) else "custom",
                    label=request.delta.get("label", request.trait_id) if isinstance(request.delta, dict) else request.trait_id,
                    value=initial_value,
                    version=1,
                    weight=request.delta.get("weight", 0.8) if isinstance(request.delta, dict) else 0.8,
                    confidence=request.delta.get("confidence", 0.7) if isinstance(request.delta, dict) else 0.7,
                    origin=request.source,
                    status="active",
                )
                import hashlib
                trait_model.checksum = hashlib.sha3_256(trait_model.value.encode("utf-8")).hexdigest()
                session.add(trait_model)

            version_entry = TraitVersionModel(
                trait_id=trait_model.trait_id,
                version=trait_model.version,
                delta=request.delta if isinstance(request.delta, dict) else {"value": request.delta},
                changed_at=datetime.now(UTC),
                changed_by=request.source,
            )
            session.add(version_entry)
            session.commit()
            session.refresh(trait_model)

            review_required = trait_model.confidence < 0.6 or "rollback" in request.reason.lower()
            return TraitUpdateResponse(trait=self._to_trait(trait_model), review_required=review_required)

    def check_governance(self, request: GovernanceCheckRequest) -> GovernanceCheckResponse:
        from .schemas import AutoFix

        issues: List[GovernanceIssue] = []
        drift_score = 0.0
        coherence_score = 1.0
        payload_bytes = len(request.draft_response.encode("utf-8"))

        # Parser les signals (array)
        for signal in request.signals:
            if signal.type == "drift":
                drift_score = signal.value
            elif signal.type == "coherence":
                coherence_score = signal.value
            elif signal.type == "payload":
                payload_bytes = int(signal.value)

        if drift_score >= self.settings.governance_threshold_block:
            issues.append(GovernanceIssue(code="DRIFT_CRITICAL", severity="error", message="Dérive critique détectée", value=drift_score))
        elif drift_score >= self.settings.governance_threshold_warn:
            issues.append(GovernanceIssue(code="DRIFT_WARN", severity="warning", message="Dérive à surveiller", value=drift_score))

        if coherence_score < 0.8:
            issues.append(
                GovernanceIssue(code="COHERENCE_LOW", severity="warning", message="Score de cohérence trop faible", value=coherence_score)
            )

        if payload_bytes > self.settings.context_payload_hard_limit_bytes:
            issues.append(
                GovernanceIssue(
                    code="PAYLOAD_OVERSIZED",
                    severity="error",
                    message="Réponse trop volumineuse",
                    value=float(payload_bytes),
                )
            )

        verdict = "allow"
        should_block = False
        for issue in issues:
            if issue.code == "DRIFT_CRITICAL" or (issue.code == "DRIFT_WARN" and issue.value and issue.value >= self.settings.governance_threshold_block):
                should_block = True
            if issue.code == "PAYLOAD_OVERSIZED":
                should_block = True

        if should_block:
            verdict = "block"
        elif issues:
            verdict = "warn"

        if verdict != "allow":
            with self._lock:
                if any(issue.code.startswith("DRIFT") for issue in issues):
                    self._drift_alerts += 1
                    # Rollback automatique si drift bloquant
                    if verdict == "block":
                        self._rollback_last_trait_update(request.session_id)

        metrics.GOVERNANCE_DECISIONS.labels(verdict=verdict).inc()

        auto_fix = None
        if verdict == "warn":
            auto_fix = AutoFix(action="revise_tone", payload={"suggestion": "Réviser le ton et compresser la réponse."})
        elif verdict == "block":
            auto_fix = AutoFix(action="block", payload={"message": "Bloquer la diffusion et demander une reformulation supervisée."})

        return GovernanceCheckResponse(verdict=verdict, issues=issues, auto_fix=auto_fix)

    def get_metrics(self) -> MetricsResponse:
        indicators = self._build_indicators()
        with self.session_factory() as session:
            kpi = MetricSnapshot(
                latency_context_ms=float(self._avg(self._context_latency_samples)),
                context_payload_bytes=int(self._avg(self._context_payload_samples)),
                coverage_traits_pct=self._coverage_traits(session),
                coherence_score=float(self._avg(self._coherence_samples)),
                drift_alerts_count=self._drift_alerts,
                ttl_purge_rate=self._ttl_purge_rate(),
                store_availability=0.995,
            )
        return MetricsResponse(indicators=indicators, kpis=kpi, window=self.settings.indicators_window)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _bootstrap_defaults(self) -> None:
        with self.session_factory() as session:
            existing_traits = session.scalar(select(func.count()).select_from(TraitModel)) or 0
            if existing_traits == 0:
                trait_objs = [
                    TraitModel(
                        trait_id="tone",
                        type="behavior",
                        label="Ton",
                        value="curieux mais calme",
                        version=1,
                        weight=0.82,
                        confidence=0.82,
                    ),
                    TraitModel(
                        trait_id="curiosity",
                        type="behavior",
                        label="Curiosité",
                        value="élevée",
                        version=1,
                        weight=0.9,
                        confidence=0.85,
                    ),
                ]
                session.add_all(trait_objs)
                # Flush pour s'assurer que les traits sont persistés avant de créer les versions
                session.flush()
                for trait in trait_objs:
                    import hashlib
                    trait.checksum = hashlib.sha3_256(trait.value.encode("utf-8")).hexdigest()
                    session.add(
                        TraitVersionModel(
                            trait_id=trait.trait_id,
                            version=1,  # Version initiale explicite
                            delta={"value": trait.value, "weight": trait.weight, "confidence": trait.confidence},
                            changed_at=datetime.now(UTC),
                            changed_by="system",
                        )
                    )

            existing_goal = session.scalar(
                select(func.count()).select_from(SessionGoalModel).where(SessionGoalModel.goal_id == "bootstrap")
            )
            if not existing_goal:
                session.add(
                    SessionGoalModel(
                        goal_id="bootstrap",
                        session_id="default",
                        priority=0.9,
                        description="Maintenir cohérence personnalité",
                        expires_at=datetime.now(UTC) + timedelta(days=30),
                        status="active",
                    )
                )
            session.commit()

    def _select_memories(self, session: Session, max_memories: int | None) -> List[Souvenir]:
        max_items = max_memories or self.settings.max_memories
        memories = session.scalars(select(SouvenirModel)).all()
        metrics.set_souvenirs_total(len(memories))
        scored: List[tuple[float, SouvenirModel]] = []
        now = datetime.now(UTC)
        for mem in memories:
            score = self._compute_memory_score(mem, now)
            scored.append((score, mem))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected_models = [mem for _, mem in scored[:max_items]]
        for model in selected_models:
            model.updated_at = now
            model.recency_score = min(1.0, model.recency_score + 0.15)  # Bump récence
            model.frequency += 1  # Incrémenter frequency
        if selected_models:
            session.commit()
        return [self._to_souvenir(mem) for mem in selected_models]

    def _compute_memory_score(self, memory: SouvenirModel, now: datetime) -> float:
        # Formule selon gouvernance_algorithmes.md : w_i=0.45, w_r=0.30, w_e=0.15, w_f=0.10
        delta_hours = max(0.0, (now - memory.updated_at).total_seconds() / 3600)
        half_life_hours = self.settings.recency_half_life_hours.get(memory.category, 24.0 * 14)  # 14 jours par défaut pour fact
        recency = math.exp(-delta_hours / half_life_hours)
        frequency_boost = math.log1p(memory.frequency)
        normalized_emotion = (memory.emotion_score + 1) / 2  # Mapping [-1,1] -> [0,1]
        return (
            0.45 * memory.importance_score
            + 0.30 * recency
            + 0.15 * normalized_emotion
            + 0.10 * frequency_boost
        )

    def _purge_expired(self, session: Session) -> None:
        now = datetime.now(UTC)
        souvenirs = session.scalars(select(SouvenirModel)).all()
        to_delete: List[str] = []
        for memory in souvenirs:
            # TTL est maintenant un datetime
            if memory.ttl < now:
                to_delete.append(memory.memory_id)
            # Aussi supprimer si score < 0.2
            elif self._compute_memory_score(memory, now) < 0.2:
                to_delete.append(memory.memory_id)
        if to_delete:
            session.execute(delete(SouvenirModel).where(SouvenirModel.memory_id.in_(to_delete)))
            session.commit()
        self._ttl_total += len(souvenirs)
        self._ttl_purged += len(to_delete)

    def _souvenir_from_interaction(self, log: InteractionModel, request: InteractionRequest) -> SouvenirModel:
        import hashlib
        memory_id = f"m-{uuid.uuid4().hex}"
        ttl_days = request.decisions.ttl_override_days or self.settings.ttl_config.get("fact", 45)
        ttl_datetime = datetime.now(UTC) + timedelta(days=ttl_days)
        content = log.response[:512]
        content_hash = hashlib.sha3_256(content.encode("utf-8")).hexdigest()
        
        # Vérifier si un souvenir avec le même hash existe déjà
        with self.session_factory() as check_session:
            existing = check_session.scalar(select(SouvenirModel).where(SouvenirModel.hash == content_hash))
            if existing:
                # Incrémenter frequency au lieu de dupliquer
                existing.frequency += 1
                existing.updated_at = datetime.now(UTC)
                check_session.commit()
                return existing
        
        # Créer nouveau souvenir
        tags_text = ",".join(request.decisions.derived_traits) if request.decisions.derived_traits else None
        emotion_val = 0.0
        if request.emotions:
            emotion_val = (request.emotions.valence + 1) / 2  # Normaliser [-1,1] -> [0,1]
        
        return SouvenirModel(
            memory_id=memory_id,
            category="alert" if log.severity == "error" else "fact",
            content=content,
            tags=tags_text,
            importance_score=min(1.0, 0.6 + 0.2 * request.scores.usefulness),
            recency_score=0.8,
            emotion_score=emotion_val,
            frequency=1,
            ttl=ttl_datetime,
            source="interaction",
            hash=content_hash,
        )

    def _build_indicators(self) -> Dict[str, float]:
        return {
            "coherence_score": float(self._avg(self._coherence_samples)),
            "drift_alerts": float(self._drift_alerts),
            "ttl_purge_rate": self._ttl_purge_rate(),
        }

    @staticmethod
    def _avg(values: Iterable[float]) -> float:
        data = list(values)
        if not data:
            return 0.0
        return sum(data) / len(data)

    def _ttl_purge_rate(self) -> float:
        if self._ttl_total == 0:
            return 0.0
        return round(self._ttl_purged / max(1, self._ttl_total), 3)

    def _coverage_traits(self, session: Session) -> float:
        total = session.scalar(select(func.count()).select_from(TraitModel)) or 0
        if total == 0:
            return 0.0
        active = session.scalar(select(func.count()).select_from(TraitModel).where(TraitModel.status == "active")) or 0
        return round(active / total, 2)

    def _rollback_last_trait_update(self, session_id: str) -> None:
        """Rollback automatique du dernier trait mis à jour lors d'un drift bloquant."""
        with self.session_factory() as session:
            # Trouver la dernière interaction de la session
            last_interaction = session.scalar(
                select(InteractionModel)
                .where(InteractionModel.session_id == session_id)
                .order_by(InteractionModel.occurred_at.desc())
                .limit(1)
            )
            if not last_interaction or not last_interaction.derived_traits:
                return
            
            # Pour chaque trait dérivé, rollback la dernière version
            for trait_id in last_interaction.derived_traits:
                trait = session.get(TraitModel, trait_id)
                if not trait or trait.version <= 1:
                    continue
                
                # Récupérer la version précédente
                prev_version = session.scalar(
                    select(TraitVersionModel)
                    .where(
                        TraitVersionModel.trait_id == trait_id,
                        TraitVersionModel.version == trait.version - 1
                    )
                )
                if prev_version and prev_version.delta:
                    # Appliquer l'inverse du delta
                    delta = prev_version.delta
                    if "value" in delta:
                        trait.value = delta["value"]
                    if "weight" in delta:
                        trait.weight = delta["weight"]
                    if "confidence" in delta:
                        trait.confidence = delta["confidence"]
                    trait.version -= 1
                    trait.last_update = datetime.now(UTC)
                    import hashlib
                    trait.checksum = hashlib.sha3_256(trait.value.encode("utf-8")).hexdigest()
                    
                    # Créer une entrée de version marquée rollback
                    rollback_version = TraitVersionModel(
                        trait_id=trait_id,
                        version=trait.version,
                        delta={"rollback": True, "reason": "drift_block"},
                        changed_at=datetime.now(UTC),
                        changed_by="system",
                    )
                    session.add(rollback_version)
            session.commit()

    @staticmethod
    def _to_trait(model: TraitModel) -> Trait:
        return Trait(
            trait_id=model.trait_id,
            type=model.type,
            label=model.label,
            value=model.value,
            version=model.version,
            weight=model.weight,
            confidence=model.confidence,
            last_update=model.last_update,
            origin=model.origin,
            status=model.status,  # type: ignore[arg-type]
        )

    @staticmethod
    def _to_session_goal(model: SessionGoalModel) -> SessionGoal:
        return SessionGoal(
            goal_id=model.goal_id,
            session_id=model.session_id,
            priority=model.priority,
            description=model.description,
            blocking_conditions=model.blocking_conditions or [],
            expires_at=model.expires_at,
        )

    def _to_souvenir(self, model: SouvenirModel) -> Souvenir:
        from .schemas import LinkRef
        # Convertir tags texte en liste
        tags_list = model.tags.split(",") if model.tags else []
        # Convertir links en LinkRef
        link_refs = [
            LinkRef(type=link.target_type, id=link.target_id)
            for link in model.links
        ]
        return Souvenir(
            memory_id=model.memory_id,
            category=model.category,  # type: ignore[arg-type]
            content=model.content,
            tags=tags_list,
            importance_score=model.importance_score,
            recency_score=model.recency_score,
            emotion_score=model.emotion_score,
            frequency=model.frequency,
            ttl=model.ttl,
            source=model.source or "interaction",
            link_refs=link_refs,
            hash=model.hash,
            created_at=model.created_at,
            last_seen_at=model.updated_at,  # Mapper updated_at vers last_seen_at pour compatibilité
        )

    @staticmethod
    def _to_interaction(model: InteractionModel) -> InteractionLog:
        return InteractionLog(
            interaction_id=model.interaction_id,
            session_id=model.session_id,
            occurred_at=model.occurred_at,
            prompt=model.prompt,
            response=model.response,
            scores=model.scores or {},
            derived_traits=model.derived_traits or [],
            anomalies=model.anomalies or [],
            severity=model.severity,  # type: ignore[arg-type]
            raw_size_bytes=model.raw_size_bytes,
        )

    # ------------------------------------------------------------------
    # Personal Goals CRUD (Étape 2.6)
    # ------------------------------------------------------------------
    def create_personal_goal(self, goal_data: PersonalGoalCreate) -> PersonalGoal:
        """Crée un nouvel objectif personnel."""
        with self._lock, self.session_factory() as session:
            goal_id = f"goal-{uuid.uuid4().hex[:12]}"
            now = datetime.now(UTC)
            
            # Calculer next_trigger_at basé sur frequency
            next_trigger = None
            if goal_data.frequency == "daily":
                next_trigger = now + timedelta(days=1)
            elif goal_data.frequency == "weekly":
                next_trigger = now + timedelta(weeks=1)
            elif goal_data.frequency == "monthly":
                next_trigger = now + timedelta(days=30)
            elif goal_data.frequency == "once":
                next_trigger = now  # Déclencher immédiatement
            
            goal_model = PersonalGoalModel(
                goal_id=goal_id,
                goal_type=goal_data.goal_type,
                description=goal_data.description,
                priority=goal_data.priority,
                status="active",
                trigger_conditions=goal_data.trigger_conditions,
                frequency=goal_data.frequency,
                created_at=now,
                next_trigger_at=next_trigger,
                metadata=goal_data.metadata,
            )
            session.add(goal_model)
            session.commit()
            return self._to_personal_goal(goal_model)

    def get_personal_goals(
        self,
        status: str | None = None,
        goal_type: str | None = None,
    ) -> List[PersonalGoal]:
        """Récupère les objectifs personnels avec filtres optionnels."""
        with self._lock, self.session_factory() as session:
            query = select(PersonalGoalModel)
            if status:
                query = query.where(PersonalGoalModel.status == status)
            if goal_type:
                query = query.where(PersonalGoalModel.goal_type == goal_type)
            goals = session.scalars(query).all()
            return [self._to_personal_goal(goal) for goal in goals]

    def get_personal_goal(self, goal_id: str) -> PersonalGoal | None:
        """Récupère un objectif personnel par ID."""
        with self._lock, self.session_factory() as session:
            goal = session.get(PersonalGoalModel, goal_id)
            return self._to_personal_goal(goal) if goal else None

    def update_personal_goal(self, goal_id: str, update_data: PersonalGoalUpdate) -> PersonalGoal | None:
        """Met à jour un objectif personnel."""
        with self._lock, self.session_factory() as session:
            goal = session.get(PersonalGoalModel, goal_id)
            if not goal:
                return None
            
            if update_data.description is not None:
                goal.description = update_data.description
            if update_data.priority is not None:
                goal.priority = update_data.priority
            if update_data.status is not None:
                goal.status = update_data.status
            if update_data.trigger_conditions is not None:
                goal.trigger_conditions = update_data.trigger_conditions
            if update_data.frequency is not None:
                goal.frequency = update_data.frequency
                # Recalculer next_trigger_at si frequency change
                if update_data.frequency == "daily":
                    goal.next_trigger_at = datetime.now(UTC) + timedelta(days=1)
                elif update_data.frequency == "weekly":
                    goal.next_trigger_at = datetime.now(UTC) + timedelta(weeks=1)
                elif update_data.frequency == "monthly":
                    goal.next_trigger_at = datetime.now(UTC) + timedelta(days=30)
            if update_data.next_trigger_at is not None:
                goal.next_trigger_at = update_data.next_trigger_at
            if update_data.metadata is not None:
                goal.metadata = update_data.metadata
            
            session.commit()
            return self._to_personal_goal(goal)

    def delete_personal_goal(self, goal_id: str) -> bool:
        """Supprime un objectif personnel."""
        with self._lock, self.session_factory() as session:
            goal = session.get(PersonalGoalModel, goal_id)
            if not goal:
                return False
            session.delete(goal)
            session.commit()
            return True

    def get_goals_to_trigger(self) -> List[PersonalGoal]:
        """Récupère les objectifs actifs qui doivent être déclenchés."""
        with self._lock, self.session_factory() as session:
            now = datetime.now(UTC)
            query = select(PersonalGoalModel).where(
                PersonalGoalModel.status == "active",
                PersonalGoalModel.next_trigger_at <= now,
            )
            goals = session.scalars(query).all()
            return [self._to_personal_goal(goal) for goal in goals]

    @staticmethod
    def _to_personal_goal(model: PersonalGoalModel) -> PersonalGoal:
        """Convertit un modèle PersonalGoalModel en schéma PersonalGoal."""
        return PersonalGoal(
            goal_id=model.goal_id,
            goal_type=model.goal_type,  # type: ignore[arg-type]
            description=model.description,
            priority=model.priority,
            status=model.status,  # type: ignore[arg-type]
            trigger_conditions=model.trigger_conditions,
            frequency=model.frequency,  # type: ignore[arg-type]
            created_at=model.created_at,
            last_triggered_at=model.last_triggered_at,
            next_trigger_at=model.next_trigger_at,
            metadata=model.metadata,
        )
