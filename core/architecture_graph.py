"""ArchitectureGraph MVP pour la self-improvement V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ModuleSpec:
    """Description d'un module interne."""

    name: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    mutable: bool = True


@dataclass(frozen=True)
class SelfModification:
    """Une modification proposée ou appliquée."""

    target_module: str
    summary: str
    author: str = "code_brain"
    timestamp_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ArchitectureGraph:
    """Carte simple de l'architecture de LIA pour pilotage self-coding."""

    modules: Dict[str, ModuleSpec] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    changelog: List[SelfModification] = field(default_factory=list)
    changelog_path: Optional[str] = None

    def register_module(self, spec: ModuleSpec) -> None:
        self.modules[spec.name] = spec

    def is_module_mutable(self, module_name: str) -> bool:
        spec = self.modules.get(module_name)
        if spec is None:
            return False
        return spec.mutable

    def add_constraint(self, rule: str) -> None:
        if rule not in self.constraints:
            self.constraints.append(rule)

    def log_modification(self, modification: SelfModification) -> None:
        self.changelog.append(modification)
        if not self.changelog_path:
            return
        try:
            path = Path(self.changelog_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "target_module": modification.target_module,
                "summary": modification.summary,
                "author": modification.author,
                "timestamp_iso": modification.timestamp_iso,
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Best-effort persistence: in-memory changelog remains source of truth.
            pass

    @classmethod
    def default_v2(cls, changelog_path: Optional[str] = None) -> "ArchitectureGraph":
        graph = cls(changelog_path=changelog_path)
        graph.register_module(ModuleSpec("neural_router", ["message"], ["intent"], mutable=True))
        graph.register_module(ModuleSpec("lang_brain", ["prompt"], ["response"], mutable=True))
        graph.register_module(ModuleSpec("code_brain", ["prompt"], ["code"], mutable=True))
        graph.register_module(ModuleSpec("identity_brain", ["response"], ["validated_response"], mutable=False))
        graph.add_constraint("identity_brain must stay immutable")
        graph.add_constraint("self_coding_sandbox cannot be self-modified")
        return graph
