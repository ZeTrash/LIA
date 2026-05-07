"""ArchitectureGraph MVP pour la self-improvement V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


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

    @classmethod
    def default_v2(cls) -> "ArchitectureGraph":
        graph = cls()
        graph.register_module(ModuleSpec("neural_router", ["message"], ["intent"], mutable=True))
        graph.register_module(ModuleSpec("lang_brain", ["prompt"], ["response"], mutable=True))
        graph.register_module(ModuleSpec("code_brain", ["prompt"], ["code"], mutable=True))
        graph.register_module(ModuleSpec("identity_brain", ["response"], ["validated_response"], mutable=False))
        graph.add_constraint("identity_brain must stay immutable")
        graph.add_constraint("self_coding_sandbox cannot be self-modified")
        return graph
