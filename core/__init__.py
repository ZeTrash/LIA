"""Noyau primaire de LIA.

Exports:
- Runtime generation: `LLMAdapter`, `CoreConfig`
- Phase 1-2 (experimental): cognitive planning primitives
"""

from .llm_adapter import LLMAdapter
from .config import CoreConfig
from .neural_router import NeuralRouter, BrainType, IntentClassification, BrainDispatchPlan
from .code_brain import CodeBrain
from .architecture_graph import ArchitectureGraph, ModuleSpec, SelfModification
from .self_coding_sandbox import SelfCodingSandbox, SandboxResult
from .self_improvement_evaluator import SelfImprovementEvaluator, BenchmarkResult, EvaluationResult

# Exports pour le système de planification cognitive (Phase 1-5)
try:
    from .cognitive_models import Action, ActionPlan, ActionType, ExecutionResult, RequestAnalysis, VerificationResult, Pattern
    from .cognitive_planner import CognitivePlanner
    from .action_executor import ActionExecutor
    from .prompt_builder import PromptBuilder, PromptSection
    from .self_verifier import SelfVerifier
    from .pattern_learner import PatternLearner
    from .cognitive_safeguards import CognitiveSafeguards, SafeguardConfig
    from .cognitive_optimizer import CognitiveOptimizer
    from .cognitive_metrics import CognitiveMetrics
    
    __all__ = [
        "LLMAdapter",
        "CoreConfig",
        "NeuralRouter",
        "BrainType",
        "IntentClassification",
        "BrainDispatchPlan",
        "CodeBrain",
        "ArchitectureGraph",
        "ModuleSpec",
        "SelfModification",
        "SelfCodingSandbox",
        "SandboxResult",
        "SelfImprovementEvaluator",
        "BenchmarkResult",
        "EvaluationResult",
        # Cognitive planning (Phase 1-5)
        "ActionType",
        "Action",
        "ActionPlan",
        "RequestAnalysis",
        "ExecutionResult",
        "VerificationResult",
        "Pattern",
        "CognitivePlanner",
        "ActionExecutor",
        "PromptSection",
        "PromptBuilder",
        "SelfVerifier",
        "PatternLearner",
        "CognitiveSafeguards",
        "SafeguardConfig",
        "CognitiveOptimizer",
        "CognitiveMetrics",
    ]
except ImportError:
    __all__ = [
        "LLMAdapter",
        "CoreConfig",
        "NeuralRouter",
        "BrainType",
        "IntentClassification",
        "BrainDispatchPlan",
        "CodeBrain",
        "ArchitectureGraph",
        "ModuleSpec",
        "SelfModification",
        "SelfCodingSandbox",
        "SandboxResult",
        "SelfImprovementEvaluator",
        "BenchmarkResult",
        "EvaluationResult",
    ]

__version__ = "0.1.0"
