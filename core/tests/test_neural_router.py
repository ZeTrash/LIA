"""Tests unitaires du NeuralRouter MVP."""

from core.neural_router import (
    BrainType,
    IntentClassification,
    NeuralRouter,
)


def test_classify_code_and_memory_multi_brain():
    router = NeuralRouter()
    intent = router.classify_intent("Peux-tu debug ce code python et te souvenir de notre échange ?")
    assert isinstance(intent, IntentClassification)
    assert intent.brain == BrainType.CODE
    assert intent.multi_brain is True
    assert BrainType.CODE in intent.required_brains
    assert BrainType.MEMORY in intent.required_brains
    assert BrainType.LANG in intent.required_brains


def test_dispatch_keeps_primary_and_parallel():
    router = NeuralRouter()
    intent = router.classify_intent("Analyse cette image et réponds.")
    plan = router.dispatch(intent)
    assert plan.primary_brain in (BrainType.VISION, BrainType.LANG)
    if plan.primary_brain == BrainType.VISION:
        assert BrainType.LANG in plan.parallel_brains


def test_aggregate_prefers_lang_response():
    router = NeuralRouter()
    output = router.aggregate(
        {
            BrainType.MEMORY: "context mem",
            BrainType.LANG: "final answer",
            BrainType.SYSTEM: "health ok",
        }
    )
    assert output == "final answer"

