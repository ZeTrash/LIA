"""Tests pour LLMAdapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.llm_adapter import LLMAdapter
from core.config import CoreConfig


@pytest.fixture
def config():
    """Configuration de test."""
    return CoreConfig(
        model_name="gpt2",
        max_length=50,
        temperature=0.7,
        quantize=False  # Désactiver quantisation pour tests
    )


@pytest.fixture
def adapter(config):
    """Adapter de test."""
    return LLMAdapter(config)


def test_config_creation(config):
    """Test création de configuration."""
    assert config.model_name == "gpt2"
    assert config.max_length == 50
    assert config.temperature == 0.7


def test_config_to_dict(config):
    """Test conversion configuration en dictionnaire."""
    data = config.to_dict()
    assert "model_name" in data
    assert "max_length" in data
    assert "temperature" in data
    assert "router_min_confidence" in data
    assert "enable_pattern_brain_remote" in data
    assert "enable_pattern_brain_local_fallback" in data


def test_config_from_dict():
    """Test création configuration depuis dictionnaire."""
    data = {
        "model_name": "gpt2",
        "max_length": 100,
        "temperature": 0.8
    }
    config = CoreConfig.from_dict(data)
    assert config.model_name == "gpt2"
    assert config.max_length == 100
    assert config.temperature == 0.8


def test_config_update(config):
    """Test mise à jour configuration."""
    config.update(temperature=0.9, max_length=150)
    assert config.temperature == 0.9
    assert config.max_length == 150


def test_adapter_initialization_mocked():
    """Test initialisation de l'adaptateur avec mocks."""
    config = CoreConfig()
    
    with patch('core.llm_adapter.LLMAdapter._load_model'), \
         patch('core.llm_adapter.LLMAdapter._detect_device', return_value="cpu"):
        adapter = LLMAdapter(config)
        assert adapter is not None
        assert adapter.config is not None
        assert adapter.device == "cpu"


def test_build_prompt_standalone():
    """Test construction de prompt sans adapter complet."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    # Créer un adapter minimal pour tester build_prompt
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    message = "Bonjour, comment vas-tu ?"
    context = {
        "traits": [
            {"label": "Ton", "value": "Amical et chaleureux"}
        ],
        "memories": [
            {"content": "L'utilisateur aime la philosophie"}
        ],
        "session_goals": []
    }
    
    prompt = adapter.build_prompt(message, context)
    
    assert "Bonjour" in prompt
    assert "Personnalité" in prompt or "Amical" in prompt
    assert message in prompt


def test_build_prompt_no_context():
    """Test construction de prompt sans contexte."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    message = "Bonjour"
    prompt = adapter.build_prompt(message, None)
    
    assert message in prompt
    assert "Bonjour" in prompt


def test_build_prompt_with_goals():
    """Test construction de prompt avec objectifs."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    message = "Test"
    context = {
        "traits": [],
        "memories": [],
        "session_goals": [
            {"description": "Explorer la philosophie"}
        ]
    }
    
    prompt = adapter.build_prompt(message, context)
    
    assert "Objectifs" in prompt
    assert "philosophie" in prompt


@pytest.mark.asyncio
async def test_generate_mocked():
    """Test génération de réponse avec mocks."""
    import sys
    
    config = CoreConfig(max_length=50)
    
    # Mock torch avant tout
    mock_torch = MagicMock()
    mock_no_grad = MagicMock()
    mock_no_grad.__enter__ = MagicMock(return_value=None)
    mock_no_grad.__exit__ = MagicMock(return_value=False)
    mock_torch.no_grad.return_value = mock_no_grad
    
    # Sauvegarder l'ancien torch si présent
    old_torch = sys.modules.get('torch')
    sys.modules['torch'] = mock_torch
    
    try:
        import os
        old_patterns_only = os.environ.get("LIA_PATTERNS_ONLY")
        os.environ["LIA_PATTERNS_ONLY"] = "1"
        # Mock du modèle et tokenizer
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        
        # Mock de la génération
        mock_outputs = MagicMock()
        mock_outputs.shape = [1, 10]
        mock_outputs[0] = MagicMock()  # Pour l'indexation
        mock_model.generate.return_value = mock_outputs
        
        # Mock tensor
        mock_tensor = MagicMock()
        mock_tensor.shape = [1, 5]
        mock_tensor.to.return_value = mock_tensor
        mock_tokenizer.encode.return_value = mock_tensor
        mock_tokenizer.decode.return_value = "=== Personnalité === Test prompt Bonjour Réponse générée"
        
        with patch('core.llm_adapter.LLMAdapter._load_model'), \
             patch('core.llm_adapter.LLMAdapter._detect_device', return_value="cpu"):
            
            adapter = LLMAdapter(config)
            adapter.model = mock_model
            adapter.tokenizer = mock_tokenizer
            adapter.device = "cpu"
            
            response = await adapter.generate("Bonjour")
            
            assert response is not None
            assert len(response) > 0
            # Vérifier que la réponse est nettoyée (pas de marqueurs)
            assert "===" not in response
    finally:
        if 'old_patterns_only' in locals():
            if old_patterns_only is None:
                os.environ.pop("LIA_PATTERNS_ONLY", None)
            else:
                os.environ["LIA_PATTERNS_ONLY"] = old_patterns_only
        # Restaurer torch
        if old_torch:
            sys.modules['torch'] = old_torch
        elif 'torch' in sys.modules:
            del sys.modules['torch']


@pytest.mark.asyncio
async def test_generate_with_planner_autonomy_mode_uses_query_brain():
    """Le mode autonomie bypass la boucle menu et exécute un plan direct."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    from core.cognitive_models import ActionPlan, Action, ActionType, ExecutionResult

    config = CoreConfig(max_length=20)
    config.autonomy_mode = "auto_with_audit"
    config.autonomy_min_plan_confidence = 0.55
    config.autonomy_require_execution_success = True

    adapter = object.__new__(LLMAdapter)
    adapter.config = config
    adapter.backend_type = "gguf"
    adapter.device = "cpu"
    adapter.model = None
    adapter.tokenizer = None
    adapter.neural_router = None
    adapter.code_brain = None
    adapter.safeguards = None
    adapter.pattern_learner = None
    adapter.memory = None

    class _Planner:
        def _analyze_request(self, message: str):
            return type("A", (), {"complexity": "simple"})()

        async def plan(self, user_message: str, session_id: str = "default"):
            return ActionPlan(
                actions=[
                    Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
                    Action(ActionType.RESPOND, {}, priority=2),
                ],
                estimated_cost=1.0,
                confidence=0.9,
            )

        def build_action_menu(self, *args, **kwargs):
            raise AssertionError("build_action_menu should not be called in autonomy mode")

    class _Executor:
        async def execute_plan(self, plan: ActionPlan, session_id: str = "default"):
            return ExecutionResult(
                results={
                    "consult_identity": {"identity": "LIA test"},
                },
                success=True,
                errors=[],
                execution_time=0.01,
            )

    adapter.cognitive_planner = _Planner()
    adapter.action_executor = _Executor()
    adapter.prompt_builder = object()
    adapter._classify_intent_with_router_model_with_confidence = lambda *a, **k: (None, 0.0)
    adapter._log_system_event = lambda *a, **k: None
    adapter._concision_profile_from_planned_actions = lambda *a, **k: "brief"
    adapter._generate_gguf = lambda prompt: "=== IDENTITÉ === ok\nRéponse générée"
    adapter._clean_response = lambda resp, *_a, **_k: resp.replace("===", "").strip()
    adapter._build_safe_fallback_response = lambda message: f"fallback for {message}"

    out = await adapter._generate_with_planner("Bonjour", session_id="s1")
    assert out


@pytest.mark.asyncio
async def test_generate_with_planner_autonomy_low_confidence_falls_back_to_menu():
    """Si la confiance du plan autonome est trop faible, on retombe sur la boucle menu."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    from core.cognitive_models import ActionPlan, Action, ActionType, ExecutionResult

    config = CoreConfig(max_length=10)
    config.autonomy_mode = "auto_with_audit"
    config.autonomy_min_plan_confidence = 0.90  # volontairement haut

    adapter = object.__new__(LLMAdapter)
    adapter.config = config
    adapter.backend_type = "gguf"
    adapter.device = "cpu"
    adapter.model = None
    adapter.tokenizer = None
    adapter.neural_router = None
    adapter.code_brain = None
    adapter.safeguards = None
    adapter.pattern_learner = None
    adapter.memory = None
    adapter._classify_intent_with_router_model_with_confidence = lambda *a, **k: (None, 0.0)
    adapter._log_system_event = lambda *a, **k: None
    adapter._concision_profile_from_planned_actions = lambda *a, **k: "brief"
    adapter._generate_gguf = lambda prompt: "Réponse"
    adapter._clean_response = lambda resp, *_a, **_k: resp
    adapter._build_safe_fallback_response = lambda message: f"fallback for {message}"

    class _Planner:
        def _analyze_request(self, message: str):
            return type("A", (), {"complexity": "simple"})()

        async def plan(self, user_message: str, session_id: str = "default"):
            # Confiance trop faible -> autonomie doit échouer
            return ActionPlan(actions=[Action(ActionType.RESPOND, {}, priority=1)], confidence=0.1)

        def build_action_menu(self, user_message: str, execution_results: dict, session_id: str):
            # Menu minimal: RESPOND
            return [Action(ActionType.RESPOND, {}, priority=1)]

    class _Executor:
        async def execute_plan(self, plan: ActionPlan, session_id: str = "default"):
            return ExecutionResult(results={}, success=True, errors=[], execution_time=0.0)

        async def execute_action(self, action: Action, session_id: str = "default", partial_results=None):
            return {"ready": True}

    adapter.cognitive_planner = _Planner()
    adapter.action_executor = _Executor()
    adapter.prompt_builder = object()

    import os
    old = os.environ.get("LIA_PATTERNS_ONLY")
    os.environ["LIA_PATTERNS_ONLY"] = "1"
    try:
        out = await adapter._generate_with_planner("Bonjour", session_id="s1")
        assert out == "Réponse"
    finally:
        if old is None:
            os.environ.pop("LIA_PATTERNS_ONLY", None)
        else:
            os.environ["LIA_PATTERNS_ONLY"] = old


@pytest.mark.asyncio
async def test_generate_with_planner_autonomy_replans_before_menu_fallback():
    """Si plan_confidence faible, QueryBrain tente un replan safe_minimal avant de tomber sur le menu."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    from core.cognitive_models import ActionPlan, Action, ActionType, ExecutionResult

    config = CoreConfig(max_length=10)
    config.autonomy_mode = "auto_with_audit"
    config.autonomy_min_plan_confidence = 0.60
    config.autonomy_max_replans = 1

    adapter = object.__new__(LLMAdapter)
    adapter.config = config
    adapter.backend_type = "gguf"
    adapter.device = "cpu"
    adapter.model = None
    adapter.tokenizer = None
    adapter.neural_router = None
    adapter.code_brain = None
    adapter.safeguards = None
    adapter.pattern_learner = None
    adapter.memory = None
    adapter._classify_intent_with_router_model_with_confidence = lambda *a, **k: (None, 0.0)
    adapter._log_system_event = lambda *a, **k: None
    adapter._concision_profile_from_planned_actions = lambda *a, **k: "brief"
    adapter._generate_gguf = lambda prompt: "Réponse"
    adapter._clean_response = lambda resp, *_a, **_k: resp
    adapter._build_safe_fallback_response = lambda message: f"fallback for {message}"

    class _Planner:
        def __init__(self):
            self.plan_calls = 0

        def _analyze_request(self, message: str):
            # déclenche replan_safe_minimal avec needs_identity
            return type("A", (), {"complexity": "simple", "needs_identity": True, "needs_memory": False})()

        async def plan(self, user_message: str, session_id: str = "default"):
            self.plan_calls += 1
            return ActionPlan(actions=[Action(ActionType.RESPOND, {}, priority=1)], confidence=0.1)

        def build_action_menu(self, *args, **kwargs):
            raise AssertionError("Menu fallback should not be reached if replan succeeds")

    class _Executor:
        async def execute_plan(self, plan: ActionPlan, session_id: str = "default"):
            # Execution OK => replan doit passer
            return ExecutionResult(results={"consult_identity": {"identity": "ok"}}, success=True, errors=[], execution_time=0.0)

    adapter.cognitive_planner = _Planner()
    adapter.action_executor = _Executor()
    adapter.prompt_builder = object()

    out = await adapter._generate_with_planner("Bonjour", session_id="s1")
    assert out == "Réponse"


@pytest.mark.asyncio
async def test_generate_with_planner_prompt_rebuild_happens_before_menu_fallback():
    """Si prompt_confidence est faible, on rebuild PromptBrain avant fallback menu."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    from core.cognitive_models import ActionPlan, Action, ActionType, ExecutionResult

    config = CoreConfig(max_length=10)
    config.autonomy_mode = "auto_with_audit"
    config.autonomy_min_plan_confidence = 0.55
    config.autonomy_prompt_min_confidence = 0.75  # forcer rebuild
    config.autonomy_max_prompt_rebuilds = 1

    adapter = object.__new__(LLMAdapter)
    adapter.config = config
    adapter.backend_type = "gguf"
    adapter.device = "cpu"
    adapter.model = None
    adapter.tokenizer = None
    adapter.neural_router = None
    adapter.code_brain = None
    adapter.safeguards = None
    adapter.pattern_learner = None
    adapter.memory = None
    adapter._classify_intent_with_router_model_with_confidence = lambda *a, **k: (None, 0.0)
    adapter._log_system_event = lambda *a, **k: None
    adapter._concision_profile_from_planned_actions = lambda *a, **k: "brief"
    adapter._generate_gguf = lambda prompt: "Réponse"
    adapter._clean_response = lambda resp, *_a, **_k: resp
    adapter._build_safe_fallback_response = lambda message: f"fallback for {message}"

    class _Planner:
        def _analyze_request(self, message: str):
            return type("A", (), {"complexity": "simple"})()

        async def plan(self, user_message: str, session_id: str = "default"):
            return ActionPlan(
                actions=[
                    Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
                    Action(ActionType.RESPOND, {}, priority=2),
                ],
                confidence=0.9,
            )

        def build_action_menu(self, *args, **kwargs):
            # Fallback menu doit arriver APRÈS une tentative de rebuild prompt.
            er = kwargs.get("execution_results") or {}
            pb = er.get("_prompt_brain") or {}
            assert pb.get("rebuilt") is True
            return [Action(ActionType.RESPOND, {}, priority=1)]

    class _Executor:
        async def execute_plan(self, plan: ActionPlan, session_id: str = "default"):
            # Pas d'identité -> PromptBrain confidence baisse, mais rebuild doit passer avec seuil atteint
            return ExecutionResult(results={}, success=True, errors=[], execution_time=0.0)

    adapter.cognitive_planner = _Planner()
    adapter.action_executor = _Executor()
    adapter.prompt_builder = object()

    import os
    old = os.environ.get("LIA_PATTERNS_ONLY")
    os.environ["LIA_PATTERNS_ONLY"] = "1"
    try:
        out = await adapter._generate_with_planner("Bonjour", session_id="s1")
        assert out == "Réponse"
    finally:
        if old is None:
            os.environ.pop("LIA_PATTERNS_ONLY", None)
        else:
            os.environ["LIA_PATTERNS_ONLY"] = old


def test_clean_response(adapter):
    """Test nettoyage de réponse."""
    dirty_response = "=== Personnalité === Bonjour  comment  vas-tu ?"
    clean = adapter._clean_response(dirty_response)
    
    assert "===" not in clean
    assert "  " not in clean  # Pas d'espaces multiples


def test_clean_response_standalone():
    """Test nettoyage de réponse sans adapter (test unitaire)."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    # Créer un adapter minimal pour tester _clean_response
    # On contourne l'initialisation complète
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    
    dirty_response = "=== Personnalité === Bonjour  comment  vas-tu ?"
    clean = adapter._clean_response(dirty_response)
    
    assert "===" not in clean
    assert "  " not in clean  # Pas d'espaces multiples


def test_clean_response_capability_query_keeps_more_sentences_standalone():
    """Les questions capacités » ne doivent pas être coupées à 320 car / 3 phrases."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    paragraphs = ". ".join(f"Je peux faire l'item {i}" for i in range(1, 9))
    short = adapter._clean_response(paragraphs, user_request="raconte ta journée.")
    boosted = adapter._clean_response(paragraphs, user_request="quelles sont tes capacités ?")
    assert boosted.count("item") >= short.count("item")
    assert boosted.count("item") >= 7


def test_clean_response_extended_profile_via_planner_standalone():
    """Mode planner : extended sans mots-clés dans la question (profil explicite)."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    paragraphs = ". ".join(f"Puce {i}." for i in range(1, 12))
    short = adapter._clean_response(paragraphs, user_request="", concision_profile="default")
    extended = adapter._clean_response(paragraphs, user_request="", concision_profile="extended")
    assert extended.count("Puce") >= 7
    assert extended.count("Puce") >= short.count("Puce")


def test_clean_response_default_profile_overrides_capability_keywords_standalone():
    """Profil planner 'default' : rester court même si l'utilisateur parle capacités."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    paragraphs = ". ".join(f"Ligne {i}." for i in range(1, 12))
    strict = adapter._clean_response(
        paragraphs,
        user_request="quelles sont tes capacités ?",
        concision_profile="default",
    )
    heuristic = adapter._clean_response(paragraphs, user_request="quelles sont tes capacités ?")
    assert strict.count("Ligne") < heuristic.count("Ligne")


def test_concision_profile_from_plan_consult_environment():
    from core.cognitive_models import Action, ActionPlan, ActionType

    adapter = LLMAdapter.__new__(LLMAdapter)
    plan = ActionPlan(
        actions=[
            Action(ActionType.CONSULT_ENVIRONMENT, {}, priority=1),
            Action(ActionType.RESPOND, {}, priority=2),
        ]
    )
    assert adapter._concision_profile_from_planned_actions(plan.sorted_actions()) == "extended"
    plan2 = ActionPlan(
        actions=[Action(ActionType.CONSULT_MEMORY, {}, priority=1), Action(ActionType.RESPOND, {}, priority=2)]
    )
    assert adapter._concision_profile_from_planned_actions(plan2.sorted_actions()) == "default"


def test_update_config(adapter):
    """Test mise à jour configuration."""
    adapter.update_config(temperature=0.9)
    assert adapter.config.temperature == 0.9


def test_update_config_standalone():
    """Test mise à jour configuration sans adapter complet."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig
    
    # Créer un adapter minimal pour tester update_config
    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig()
    adapter.config.enable_auto_calibration = True
    
    adapter.update_config(temperature=0.9)
    assert adapter.config.temperature == 0.9


def test_router_model_classification_with_confidence_exact_label():
    """Le routeur modèle renvoie un label exact avec confiance élevée."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(enable_real_brain_routing=True)
    adapter._ensure_router_brain = lambda: None

    mock_router_model = Mock()
    mock_output = Mock()
    mock_output.outputs = [Mock(text="CODE")]
    mock_router_model.generate.return_value = [mock_output]
    adapter.router_brain_model = mock_router_model

    label, confidence = adapter._classify_intent_with_router_model_with_confidence(
        "corrige ce bug python"
    )

    assert label == "CODE"
    assert confidence >= 0.9


def test_router_model_classification_with_confidence_disabled():
    """Si le routing modèle est désactivé, aucun label n'est utilisé."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(enable_real_brain_routing=False)
    adapter._ensure_router_brain = lambda: None
    adapter.router_brain_model = None

    label, confidence = adapter._classify_intent_with_router_model_with_confidence(
        "analyse cette image"
    )

    assert label is None
    assert confidence == 0.0


def test_router_model_classification_with_transformers_backend_path():
    """Le routing LLM fonctionne aussi avec backend transformers principal."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(enable_real_brain_routing=True)
    adapter._ensure_router_brain = lambda: None
    adapter.router_brain_model = None
    adapter.backend_type = "transformers"
    adapter.device = "cpu"

    mock_tokenizer = Mock()
    mock_tensor = MagicMock()
    mock_tensor.shape = [1, 5]
    mock_tensor.to.return_value = mock_tensor
    mock_tokenizer.return_value = {"input_ids": mock_tensor, "attention_mask": mock_tensor}
    mock_tokenizer.decode.return_value = "LANG"
    mock_tokenizer.pad_token_id = 0
    mock_tokenizer.eos_token_id = 1

    mock_model = Mock()
    mock_output = MagicMock()
    mock_output.__getitem__.return_value = mock_tensor
    mock_model.generate.return_value = [mock_output]

    adapter.tokenizer = mock_tokenizer
    adapter.model = mock_model

    with patch("torch.no_grad") as mock_no_grad:
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = False
        mock_no_grad.return_value = cm
        label, confidence = adapter._classify_intent_with_router_model_with_confidence("bonjour")

    assert label == "LANG"
    assert confidence >= 0.9


def test_safe_fallback_response_greeting():
    from core.llm_adapter import LLMAdapter

    text = LLMAdapter._build_safe_fallback_response("Bonjour")
    assert "Bonjour" in text
    assert "aider" in text


def test_safe_fallback_response_generic():
    from core.llm_adapter import LLMAdapter

    text = LLMAdapter._build_safe_fallback_response("Explique moi ce bug")
    assert "reformuler" in text


def test_semantic_decision_guidance_identity():
    from core.llm_adapter import LLMAdapter
    from core.cognitive_models import Action, ActionType

    menu = [
        Action(ActionType.CONSULT_IDENTITY, {}, priority=1),
        Action(ActionType.RESPOND, {}, priority=2),
    ]
    msg = LLMAdapter._semantic_decision_guidance("identity", menu)
    assert "identity" in msg
    assert "consult_identity" in msg
    assert "respond" in msg


def test_semantic_decision_guidance_system():
    from core.llm_adapter import LLMAdapter
    from core.cognitive_models import Action, ActionType

    menu = [
        Action(ActionType.CONSULT_ENVIRONMENT, {}, priority=1),
        Action(ActionType.RESPOND, {}, priority=2),
    ]
    msg = LLMAdapter._semantic_decision_guidance("system", menu)
    assert "system" in msg
    assert "consult_environment" in msg


def test_pattern_brain_local_fallback_gguf():
    """Le fallback local pattern_brain fonctionne en backend GGUF."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(
        enable_pattern_brain_remote=False,
        enable_pattern_brain_local_fallback=True,
    )
    adapter.model = object()
    adapter.backend_type = "gguf"
    adapter._build_pattern_gemini_question = Mock(return_value="prompt")
    adapter._generate_gguf = Mock(return_value="{{memoire},{B2, G4, G5}}")

    sequence, raw = adapter._recommend_pattern_sequence_with_local_llm(
        user_request="que sais tu de moi",
        executed_sequence=["B1"],
    )

    assert sequence == ["B2", "G4", "G5"]
    assert raw


def test_pattern_brain_local_fallback_requires_model():
    """Sans modèle chargé, le fallback local ne propose rien."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(
        enable_pattern_brain_remote=False,
        enable_pattern_brain_local_fallback=True,
    )
    adapter.model = None
    adapter.backend_type = "gguf"

    sequence, raw = adapter._recommend_pattern_sequence_with_local_llm(
        user_request="bonjour",
        executed_sequence=[],
    )

    assert sequence == []
    assert raw == ""


@pytest.mark.asyncio
async def test_recommend_pattern_sequence_source_local_fallback():
    """Le mode hybride expose bien `pattern_source=local_fallback`."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(
        enable_pattern_brain_remote=False,
        enable_pattern_brain_local_fallback=True,
    )
    adapter._recommend_pattern_sequence_with_local_llm = Mock(
        return_value=(["B2", "G4", "G5"], "{{memoire},{B2, G4, G5}}")
    )

    sequence, raw, source = await adapter._recommend_pattern_sequence_with_brain(
        user_request="que connais tu de moi",
        executed_sequence=["B1"],
    )

    assert sequence == ["B2", "G4", "G5"]
    assert raw
    assert source == "local_fallback"


@pytest.mark.asyncio
async def test_recommend_pattern_sequence_source_none():
    """Sans remote ni fallback local, la source est `none`."""
    from core.llm_adapter import LLMAdapter
    from core.config import CoreConfig

    adapter = object.__new__(LLMAdapter)
    adapter.config = CoreConfig(
        enable_pattern_brain_remote=False,
        enable_pattern_brain_local_fallback=False,
    )

    sequence, raw, source = await adapter._recommend_pattern_sequence_with_brain(
        user_request="bonjour",
        executed_sequence=[],
    )

    assert sequence == []
    assert raw == ""
    assert source == "none"

