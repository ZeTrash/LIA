"""Adapter pour modèles LLM locaux (noyau primaire)."""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable, List, TYPE_CHECKING

from .config import CoreConfig

logger = logging.getLogger(__name__)

# URL du service "pattern-brain" (noyau subconscient) pour les recommandations de patterns
PATTERN_BRAIN_URL = os.getenv(
    "LIA_PATTERN_BRAIN_URL",
    "http://127.0.0.1:8002/patterns/recommend",
)

# Catalogue d'actions pour le système de patterns (menus base/général).
# Doit rester cohérent avec `scripts/test_patterns_gemini.py` et `support/pattern_brain_service.py`.
PATTERN_ACTIONS_CATALOG: Dict[str, str] = {
    # Base menu
    "B1": "Voir la demande de l'utilisateur.",
    "B2": "Consulter ma mémoire et me connaitre (menu général).",
    "B3": "Répondre à la requête de l'utilisateur.",
    # General menu
    "G1": "Connaitre mon identité (qui je suis globalement).",
    "G2": "Consulter UNIQUEMENT mes traits (caractéristiques internes : personnalité, façons d'être, styles).",
    "G3": "Consulter UNIQUEMENT mon environnement et mes capacités (ce que je peux ou ne peux pas faire).",
    "G4": "Consulter mes souvenirs et faits mémorisés (événements passés, informations externes, détails contextuels).",
    "G5": "Répondre à la requête de l'utilisateur.",
    "G6": "Revenir au menu précédent.",
}

if TYPE_CHECKING:
    # Pour les annotations de type sans import circulaire
    from .cognitive_models import ResponseChunk

# Mode debug minimal : n'afficher que la boucle de menus + réponse finale,
# sans apprentissage ni métriques/mémoire.
# Par défaut, ce mode est ACTIVÉ pour revenir à la phase d'exemple simple
# décrite dans `docs/memory_performing/exemple_process.md`.
_debug_flag_raw = os.getenv("LIA_DEBUG_MINIMAL_MENU_LOOP")
if _debug_flag_raw is None:
    # Valeur par défaut : mode minimal ON
    DEBUG_MINIMAL_MENU_LOOP = True
else:
    DEBUG_MINIMAL_MENU_LOOP = str(_debug_flag_raw).lower() in {"1", "true", "yes", "oui"}

# Import optionnel de la mémoire
try:
    from memory_service.memory_adapter import MemoryAdapter
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Service mémoire non disponible")

# Import optionnel du PhraseMemoryProcessor (MemoryRank V2)
try:
    from memory_service.phrase_memory_processor import PhraseMemoryProcessor
    PHRASE_MEMORY_AVAILABLE = True
except ImportError:
    PHRASE_MEMORY_AVAILABLE = False
    logger.debug("PhraseMemoryProcessor non disponible (MemoryRank V2)")

# Import optionnel du MemoryActivator
try:
    from .memory_activator import MemoryActivator
    MEMORY_ACTIVATOR_AVAILABLE = True
except ImportError:
    MEMORY_ACTIVATOR_AVAILABLE = False
    logger.warning("MemoryActivator non disponible")

# Import optionnel de EnvironmentAwareness
try:
    from .environment_awareness import EnvironmentAwareness
    ENVIRONMENT_AWARENESS_AVAILABLE = True
except ImportError:
    ENVIRONMENT_AWARENESS_AVAILABLE = False
    logger.warning("EnvironmentAwareness non disponible")

# Import optionnel de AutonomousActionManager
try:
    from .autonomous_actions import AutonomousActionManager
    AUTONOMOUS_ACTIONS_AVAILABLE = True
except ImportError:
    AUTONOMOUS_ACTIONS_AVAILABLE = False
    logger.warning("AutonomousActionManager non disponible")

# Import optionnel du canal Support
try:
    from support.support_channel import SupportChannel
    SUPPORT_CHANNEL_AVAILABLE = True
except ImportError:
    SUPPORT_CHANNEL_AVAILABLE = False
    logger.debug("SupportChannel non disponible pour streaming")

# Import optionnel du système de planification cognitive (Phase 2)
try:
    from .cognitive_planner import CognitivePlanner
    from .action_executor import ActionExecutor
    from .prompt_builder import PromptBuilder
    from .self_verifier import SelfVerifier
    COGNITIVE_PLANNER_AVAILABLE = True
except ImportError as e:
    COGNITIVE_PLANNER_AVAILABLE = False
    logger.debug(f"Composants de planification cognitive non disponibles: {e}")

# Import optionnel du système de planification cognitive (Phase 2)
try:
    from .cognitive_planner import CognitivePlanner
    from .action_executor import ActionExecutor
    from .prompt_builder import PromptBuilder
    from .self_verifier import SelfVerifier
    COGNITIVE_PLANNER_AVAILABLE = True
except ImportError as e:
    COGNITIVE_PLANNER_AVAILABLE = False
    logger.debug(f"Composants de planification cognitive non disponibles: {e}")


class LLMAdapter:
    """Adapter pour modèles LLM locaux - Moteur de génération."""
    
    # Cache global du modèle (évite rechargement)
    _model_cache = None
    _tokenizer_cache = None
    _use_gguf = False  # Flag pour indiquer si on utilise GGUF
    _model_name_cache = None  # Nom du modèle en cache pour affichage
    
    def __init__(
        self, 
        config: Optional[CoreConfig] = None, 
        use_memory: bool = True, 
        gemini_adapter=None, 
        support_channel=None,
        use_cognitive_planner: bool = True,  # Activé par défaut maintenant
        cognitive_decision_mode: str = "menu",  # "menu" (agent chooses)
        use_phrase_memory: bool = True,  # Activer MemoryRank V2 (traitement par phrases) - Activé par défaut
    ):
        """
        Initialise l'adaptateur GPT-2.
        
        Args:
            config: Configuration du noyau primaire (optionnel)
            use_memory: Activer l'intégration avec la mémoire (défaut: True)
            gemini_adapter: Adaptateur Gemini pour la conscience environnementale (optionnel, utilisé si support_channel non fourni)
            support_channel: Canal Support pour échange avec noyau d'appui (optionnel, préféré)
            use_cognitive_planner: Activer le système de planification cognitive (Phase 2-6, défaut: True)
            cognitive_decision_mode:
                - "menu": LIA choisit itérativement la prochaine action interne (propose → choisit → exécute → répète → RESPOND)
        """
        self.config = config or CoreConfig()
        self.model = None
        self.tokenizer = None
        self.device = self._detect_device()
        # Dernière trace structurée (processus + réponse), pour interfaces avancées
        self._last_trace_chunks: List["ResponseChunk"] = []
        
        # Initialiser la mémoire si disponible et activée
        self.memory = None
        self.memory_activator = None
        self.phrase_processor = None
        if use_memory and MEMORY_AVAILABLE:
            try:
                self.memory = MemoryAdapter()
                # Initialiser le MemoryActivator pour activer la mémoire
                if MEMORY_ACTIVATOR_AVAILABLE:
                    self.memory_activator = MemoryActivator(memory_adapter=self.memory)
                    logger.info("✅ Mémoire et MemoryActivator intégrés au noyau primaire")
                else:
                    logger.info("✅ Mémoire intégrée au noyau primaire")
                
                # Initialiser le PhraseMemoryProcessor si activé (MemoryRank V2)
                if use_phrase_memory and PHRASE_MEMORY_AVAILABLE:
                    try:
                        from memory_service.store import MemoryStore
                        store = MemoryStore(use_memory_rank=True)
                        self.phrase_processor = PhraseMemoryProcessor(memory_store=store)
                        logger.info("✅ PhraseMemoryProcessor (MemoryRank V2) activé")
                    except Exception as e:
                        logger.warning(f"⚠️  Impossible d'initialiser PhraseMemoryProcessor: {e}")
            except Exception as e:
                logger.warning(f"⚠️  Impossible d'initialiser la mémoire: {e}")
        
        # Extraire gemini_adapter depuis support_channel si nécessaire
        # (pour EnvironmentAwareness qui a besoin de gemini_adapter directement)
        actual_gemini_adapter = gemini_adapter
        if support_channel and not gemini_adapter:
            # Extraire gemini_adapter depuis le canal Support
            if hasattr(support_channel, 'gemini') and support_channel.gemini:
                actual_gemini_adapter = support_channel.gemini
                logger.debug("GeminiAdapter extrait depuis SupportChannel pour EnvironmentAwareness")
        
        # Conserver une référence directe pour l'apprentissage de patterns (SYSTEME_PATTERNS)
        # Préférer Groq si disponible, sinon fallback sur Gemini
        self.gemini_adapter = actual_gemini_adapter
        self.groq_adapter = None
        if support_channel and hasattr(support_channel, 'groq') and support_channel.groq:
            self.groq_adapter = support_channel.groq
        elif not support_channel and gemini_adapter:
            # Essayer de créer GroqAdapter depuis la config si disponible
            try:
                from support.groq_adapter import GroqAdapter
                from support.config import SupportConfig
                support_config = SupportConfig()
                support_config.load_from_file()
                if support_config.groq_api_key and support_config.groq_api_key != "YOUR_GROQ_API_KEY_HERE":
                    self.groq_adapter = GroqAdapter(support_config)
                    logger.info("✅ GroqAdapter initialisé pour les patterns")
            except Exception as e:
                logger.debug(f"GroqAdapter non disponible: {e}")
        
        # Initialiser la conscience environnementale
        self.env_awareness = None
        if ENVIRONMENT_AWARENESS_AVAILABLE:
            try:
                self.env_awareness = EnvironmentAwareness(
                    memory_adapter=self.memory,
                    gemini_adapter=actual_gemini_adapter
                )
                logger.info("✅ Conscience environnementale initialisée")
            except Exception as e:
                logger.warning(f"⚠️  Impossible d'initialiser la conscience environnementale: {e}")
        
        # Initialiser le gestionnaire d'actions autonomes
        # Préférer support_channel si fourni, sinon utiliser gemini_adapter
        self.autonomous_manager = None
        if AUTONOMOUS_ACTIONS_AVAILABLE and (support_channel or gemini_adapter):
            try:
                # Pour AutonomousActionManager, utiliser gemini_adapter depuis support_channel si nécessaire
                manager_gemini = gemini_adapter
                if support_channel and not gemini_adapter:
                    if hasattr(support_channel, 'gemini') and support_channel.gemini:
                        manager_gemini = support_channel.gemini
                
                self.autonomous_manager = AutonomousActionManager(
                    memory_adapter=self.memory,
                    gemini_adapter=manager_gemini,
                    support_channel=support_channel
                )
                logger.info("✅ Gestionnaire d'actions autonomes initialisé")
            except Exception as e:
                logger.warning(f"⚠️  Impossible d'initialiser le gestionnaire d'actions autonomes: {e}")
        
        # Initialiser le système de planification cognitive (Phase 2-5)
        self.cognitive_planner = None
        self.action_executor = None
        self.prompt_builder = None
        self.self_verifier = None
        self.pattern_learner = None
        self.memory_manager = None  # Phase 4: gestion intelligente de la mémoire
        self.safeguards = None  # Phase 5: garde-fous
        self.optimizer = None  # Phase 5: optimisations
        self.metrics = None  # Phase 5: métriques
        self.use_cognitive_planner = use_cognitive_planner
        self.cognitive_decision_mode = cognitive_decision_mode

        # Sérialiser les apprentissages patterns (éviter plusieurs calls concurrentes sur le modèle)
        self._patterns_learning_lock = asyncio.Lock()
        # Derniers éléments nécessaires pour apprentissage patterns différé
        self._last_patterns_plan = None
        self._last_patterns_request: Optional[str] = None

        # Project requirement: no heuristic fallback decision mode.
        if self.cognitive_decision_mode != "menu":
            raise ValueError(
                'Unsupported cognitive_decision_mode. Only "menu" is allowed (no heuristic fallback).'
            )
        
        if use_cognitive_planner and COGNITIVE_PLANNER_AVAILABLE:
            try:
                # Initialiser PatternLearner (Phase 3) uniquement hors mode minimal
                if not DEBUG_MINIMAL_MENU_LOOP:
                    try:
                        from .pattern_learner import PatternLearner
                        pattern_config = {
                            "min_success_rate": 0.7,
                            "min_usage_count": 5,
                            "update_interval_hours": 24
                        }
                        self.pattern_learner = PatternLearner(
                            memory_adapter=self.memory,
                            config=pattern_config
                        )
                        logger.info("✅ PatternLearner initialisé (Phase 3)")
                    except Exception as e:
                        logger.warning(f"⚠️  PatternLearner non disponible: {e}")
                        self.pattern_learner = None
                
                # Configuration du planificateur
                planner_config = {
                    "max_depth": 3,
                    "reflection_budget_tokens": 500,
                    "reflection_budget_time": 2.0,
                    "default_interactions_limit": 5,
                    "default_memories_limit": 5,
                    "default_memory_limit": 5
                }
                
                self.cognitive_planner = CognitivePlanner(
                    memory_adapter=self.memory,
                    pattern_learner=self.pattern_learner,  # Phase 3: intégration
                    config=planner_config
                )
                
                self.action_executor = ActionExecutor(
                    memory_adapter=self.memory,
                    gemini_adapter=actual_gemini_adapter,
                    pattern_learner=self.pattern_learner,  # Phase 3: intégration
                    environment_awareness=self.env_awareness  # Intégration EnvironmentAwareness
                )
                
                self.prompt_builder = PromptBuilder(max_memories=3, max_interactions=3)
                
                # Initialiser les phases avancées uniquement hors mode minimal
                if not DEBUG_MINIMAL_MENU_LOOP:
                    verifier_config = {
                        "min_relevance_score": 0.6,
                        "min_memory_usage_score": 0.5,
                        "min_identity_coherence_score": 0.7,
                        "min_overall_score": 0.65
                    }
                    self.self_verifier = SelfVerifier(
                        memory_adapter=self.memory,
                        config=verifier_config
                    )
                    
                    # Initialiser MemoryManager (Phase 4)
                    try:
                        from memory_service.memory_manager import MemoryManager
                        memory_config = {
                            "min_importance_score": 0.6,
                            "max_memories_per_interaction": 3,
                            "enable_auto_cleanup": True
                        }
                        self.memory_manager = MemoryManager(
                            memory_adapter=self.memory,
                            config=memory_config
                        )
                        logger.info("✅ MemoryManager initialisé (Phase 4)")
                    except Exception as e:
                        logger.warning(f"⚠️  MemoryManager non disponible: {e}")
                        self.memory_manager = None
                    
                    # Initialiser garde-fous, optimisations et métriques (Phase 5)
                    try:
                        from .cognitive_safeguards import CognitiveSafeguards, SafeguardConfig
                        from .cognitive_optimizer import CognitiveOptimizer
                        from .cognitive_metrics import CognitiveMetrics
                        
                        # Note: sur modèle local CPU, 2s est trop bas pour une décision LLM.
                        # On garde un garde-fou, mais avec un budget temps réaliste.
                        safeguard_config = SafeguardConfig(
                            max_decision_depth=3,
                            max_reflection_tokens=500,
                            max_reflection_time=20.0,
                            max_memory_access_cost=100.0,
                            max_actions_per_plan=10,
                            enable_loop_detection=True,
                            max_loop_iterations=3
                        )
                        self.safeguards = CognitiveSafeguards(config=safeguard_config)
                        
                        optimizer_config = {
                            "enable_cache": True,
                            "cache_size": 100,
                            "cache_ttl_seconds": 3600.0,
                            "enable_parallelization": True,
                            "enable_prompt_optimization": True
                        }
                        self.optimizer = CognitiveOptimizer(config=optimizer_config)
                        
                        metrics_config = {
                            "max_metrics_history": 1000
                        }
                        self.metrics = CognitiveMetrics(config=metrics_config)
                        
                        logger.info("✅ Garde-fous, optimisations et métriques initialisés (Phase 5)")
                    except Exception as e:
                        logger.warning(f"⚠️  Phase 5 non disponible: {e}")
                        self.safeguards = None
                        self.optimizer = None
                        self.metrics = None
                    
                    # Mettre à jour CognitivePlanner avec garde-fous et optimisations
                    if self.cognitive_planner:
                        self.cognitive_planner.safeguards = self.safeguards
                        self.cognitive_planner.optimizer = self.optimizer
                
                logger.info("✅ Système de planification cognitive initialisé (Phase 2-5, mode minimal=%s)", DEBUG_MINIMAL_MENU_LOOP)
            except Exception as e:
                error_msg = f"❌ ERREUR CRITIQUE: Impossible d'initialiser le système de planification cognitive: {e}"
                logger.error(error_msg, exc_info=True)
                # PAS DE FALLBACK - lever l'exception pour voir les erreurs
                raise RuntimeError(error_msg) from e
        
        # Charger le modèle si pas en cache
        if LLMAdapter._model_cache is None:
            self._load_model()
            # Afficher le nom du modèle chargé (pour être sûr qu'il soit visible)
            if LLMAdapter._model_name_cache:
                print(f"\n✅ Modèle chargé: {LLMAdapter._model_name_cache}\n")
        else:
            self.model = LLMAdapter._model_cache
            self.tokenizer = LLMAdapter._tokenizer_cache
            # Le flag _use_gguf est déjà défini lors du premier chargement
            # Afficher le nom du modèle depuis le cache
            if LLMAdapter._model_name_cache:
                logger.info(f"✅ Modèle réutilisé depuis le cache: {LLMAdapter._model_name_cache}")
                print(f"\n✅ Modèle réutilisé: {LLMAdapter._model_name_cache}\n")
    
    def _detect_device(self) -> str:
        """Détecte le device (GPU/CPU)."""
        if self.config.device != "auto":
            return self.config.device
        
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"🚀 GPU détecté: {torch.cuda.get_device_name(0)}")
                return "cuda"
            else:
                logger.info("⚠️  GPU non disponible, utilisation du CPU")
                return "cpu"
        except ImportError:
            logger.warning("⚠️  PyTorch non disponible, utilisation du CPU")
            return "cpu"
    
    def _get_model_path(self) -> str:
        """Détermine le chemin du modèle (local ou nom pour téléchargement)."""
        if self.config.model_path:
            # Utiliser le chemin local spécifié
            model_path = Path(self.config.model_path)
            if model_path.exists():
                logger.info(f"Utilisation du modèle local: {model_path}")
                return str(model_path)
            else:
                logger.warning(f"Chemin local {model_path} n'existe pas, téléchargement depuis HuggingFace")
        
        # Vérifier si le modèle existe dans le dossier local_models_dir
        local_models_dir = Path(self.config.local_models_dir)
        if local_models_dir.exists():
            model_local_path = local_models_dir / self.config.model_name
            if model_local_path.exists():
                logger.info(f"Modèle trouvé localement: {model_local_path}")
                return str(model_local_path)
        
        # Sinon, utiliser le nom du modèle (sera téléchargé depuis HuggingFace)
        logger.info(f"Téléchargement du modèle depuis HuggingFace: {self.config.model_name}")
        return self.config.model_name
    
    def _find_gguf_model(self) -> Optional[str]:
        """Trouve un modèle GGUF dans les dossiers locaux."""
        # Si chemin GGUF spécifié explicitement
        if self.config.gguf_model_path:
            gguf_path = Path(self.config.gguf_model_path)
            if gguf_path.exists() and gguf_path.suffix == ".gguf":
                model_name = gguf_path.name
                logger.info(f"🔍 Modèle GGUF spécifié: {model_name}")
                logger.info(f"   Chemin: {gguf_path}")
                return str(gguf_path)
            elif gguf_path.exists():
                logger.warning(f"⚠️  Chemin spécifié n'est pas un fichier .gguf: {gguf_path}")
        
        # Chercher dans local_models_dir
        local_models_dir = Path(self.config.local_models_dir)
        if local_models_dir.exists():
            # Chercher récursivement tous les fichiers .gguf
            for gguf_file in local_models_dir.rglob("*.gguf"):
                model_name = gguf_file.name
                logger.info(f"🔍 Modèle GGUF trouvé dans {local_models_dir}: {model_name}")
                logger.info(f"   Chemin: {gguf_file}")
                return str(gguf_file)
        
        # Chercher dans le dossier models à la racine
        root_models = Path("models")
        if root_models.exists():
            for gguf_file in root_models.rglob("*.gguf"):
                model_name = gguf_file.name
                logger.info(f"🔍 Modèle GGUF trouvé dans models/: {model_name}")
                logger.info(f"   Chemin: {gguf_file}")
                return str(gguf_file)
        
        return None
    
    def _load_model(self):
        """Charge le modèle LLM avec quantisation optionnelle."""
        # DÉCISION: CPU → GGUF, GPU → transformers + bitsandbytes
        should_use_gguf = (
            self.config.use_gguf and 
            (self.device == "cpu" or not self._has_cuda())
        )
        
        if should_use_gguf:
            gguf_path = self._find_gguf_model()
            if gguf_path:
                try:
                    self._load_model_gguf(gguf_path)
                    LLMAdapter._use_gguf = True
                    return
                except Exception as e:
                    logger.warning(f"⚠️  Erreur chargement GGUF: {e}, fallback vers transformers...")
                    # Fallback vers transformers
            else:
                logger.warning("⚠️  Aucun modèle GGUF trouvé, utilisation de transformers (nécessite GPU pour quantisation)")
        
        # Chargement avec transformers (GPU ou fallback)
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            model_path = self._get_model_path()
            # Extraire le nom du modèle pour les logs
            if Path(model_path).exists():
                model_name = Path(model_path).name
            else:
                # Extraire le nom depuis le chemin HuggingFace
                model_name = model_path.split("/")[-1] if "/" in model_path else model_path
                # Nettoyer le nom (enlever les préfixes)
                if model_name.startswith("Qwen/"):
                    model_name = model_name.replace("Qwen/", "")
            
            logger.info("=" * 60)
            logger.info(f"📦 Chargement modèle transformers: {model_name}")
            logger.info(f"   Chemin: {model_path}")
            
            # Quantisation INT4 si activée (uniquement sur GPU)
            if self.config.quantize and self.config.quantization_bits == 4:
                # Vérifier si CUDA est disponible (bitsandbytes nécessite CUDA)
                if self.device != "cuda" or not torch.cuda.is_available():
                    logger.warning("⚠️  Quantisation INT4 nécessite CUDA (GPU non disponible). "
                                 "Pour CPU, utilisez GGUF avec use_gguf=True")
                    self._load_model_no_quant()
                else:
                    try:
                        from transformers import BitsAndBytesConfig
                        
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4"
                        )
                        
                        self.model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            quantization_config=quantization_config,
                            device_map="auto",
                            trust_remote_code=True  # Nécessaire pour Qwen
                        )
                        logger.info("✅ Quantisation INT4 activée (bitsandbytes)")
                    except ImportError:
                        logger.warning("⚠️  bitsandbytes non disponible, chargement sans quantisation...")
                        self._load_model_no_quant()
                    except Exception as e:
                        logger.warning(f"⚠️  Erreur quantisation INT4: {e}, chargement sans quantisation...")
                        self._load_model_no_quant()
            elif self.config.quantize and self.config.quantization_bits == 8:
                self._load_model_int8()
            else:
                self._load_model_no_quant()
            
            # Charger tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True  # Nécessaire pour Qwen
            )
            
            # Configurer pad_token si nécessaire
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            
            self.model.eval()
            
            # Cache global
            LLMAdapter._model_cache = self.model
            LLMAdapter._tokenizer_cache = self.tokenizer
            LLMAdapter._use_gguf = False
            LLMAdapter._model_name_cache = model_name  # Stocker le nom pour réutilisation
            
            quant_info = f"{self.config.quantization_bits} bits" if self.config.quantize else "sans quantisation"
            logger.info(f"✅ Modèle transformers chargé avec succès: {model_name}")
            logger.info(f"   Backend: {self.device.upper()}, Quantisation: {quant_info}")
            logger.info("=" * 60)
            
        except ImportError:
            raise ImportError(
                "transformers et torch sont requis pour LLMAdapter. "
                "Installez-les avec: pip install transformers torch"
            )
    
    def _has_cuda(self) -> bool:
        """Vérifie si CUDA est disponible."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _load_model_gguf(self, gguf_path: str):
        """Charge un modèle GGUF avec llama-cpp-python (CPU-only, optimisé)."""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python est requis pour charger des modèles GGUF. "
                "Installez-le avec: pip install llama-cpp-python"
            )
        
        # Extraire le nom du fichier pour les logs
        model_filename = Path(gguf_path).name
        logger.info("=" * 60)
        logger.info(f"📦 Chargement modèle GGUF: {model_filename}")
        logger.info(f"   Chemin: {gguf_path}")
        
        # Déterminer n_ctx (context window) basé sur max_prompt_length
        n_ctx = min(self.config.max_prompt_length, 131072)  # Limiter à 4K pour économiser RAM
        
        # Déterminer n_threads (nombre de threads CPU)
        import os
        n_threads = os.cpu_count() or 4
        
        # Déterminer un chat_format adapté (réduit les fuites de prompt en mode chat)
        chat_format = None
        lower_name = model_filename.lower()
        if "llama-3" in lower_name or "llama3" in lower_name:
            chat_format = "llama-3"
        elif "llama-2" in lower_name or "llama2" in lower_name:
            chat_format = "llama-2"

        # Charger le modèle GGUF
        self.model = Llama(
            model_path=gguf_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=512,  # Batch size pour traitement
            verbose=False,
            chat_format=chat_format,
            # Paramètres de génération par défaut
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            repeat_penalty=self.config.repetition_penalty,
        )
        
        # Pour GGUF, on n'a pas besoin de tokenizer séparé (intégré dans Llama)
        # Mais on crée un objet tokenizer factice pour compatibilité
        self.tokenizer = None  # GGUF gère la tokenisation en interne
        
        # Cache global
        LLMAdapter._model_cache = self.model
        LLMAdapter._tokenizer_cache = None
        LLMAdapter._model_name_cache = model_filename  # Stocker le nom pour réutilisation
        
        logger.info(f"✅ Modèle GGUF chargé avec succès: {model_filename}")
        logger.info(f"   Backend: CPU (llama.cpp)")
        logger.info(f"   Threads: {n_threads}, Context: {n_ctx} tokens")
        logger.info("=" * 60)
    
    def _load_model_no_quant(self):
        """Charge le modèle sans quantisation."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        model_path = self._get_model_path()
        # Extraire le nom du modèle
        if Path(model_path).exists():
            model_name = Path(model_path).name
        else:
            model_name = model_path.split("/")[-1] if "/" in model_path else model_path
            if model_name.startswith("Qwen/"):
                model_name = model_name.replace("Qwen/", "")
        
        logger.info(f"   Chargement sans quantisation: {model_name}")
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        if self.device != "cuda" or "device_map" not in str(type(self.model)):
            self.model.to(self.device)
        self.model.eval()
    
    def _load_model_int8(self):
        """Charge le modèle avec quantisation INT8 (fallback)."""
        self._load_model_no_quant()  # Pour l'instant, on utilise la même méthode
        logger.info("Quantisation INT8 (fallback vers sans quantisation)")
    
    def build_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Construit le prompt avec contexte mémoire.
        
        Args:
            message: Message de l'utilisateur (peut contenir des sections spéciales comme INFORMATION EXTERNE)
            context: Contexte mémoire (traits, souvenirs, etc.)
        
        Returns:
            Prompt complet formaté
        """
        # Rendre robuste aux initialisations partielles (tests utilisent object.__new__)
        memory = getattr(self, "memory", None)
        env_awareness = getattr(self, "env_awareness", None)

        # Extraire l'information Gemini si présente dans le message
        gemini_info = None
        user_message = message
        
        if "=== INFORMATION EXTERNE (GEMINI) ===" in message:
            parts = message.split("=== INFORMATION EXTERNE (GEMINI) ===")
            user_message = parts[0].strip()
            if len(parts) > 1:
                gemini_section = parts[1].split("=== FIN INFORMATION EXTERNE ===")
                if len(gemini_section) > 0:
                    gemini_info = gemini_section[0].strip()
                    # Extraire la question et la réponse
                    if "Question posée à Gemini:" in gemini_info:
                        gemini_parts = gemini_info.split("Réponse de Gemini:")
                        gemini_question = gemini_parts[0].replace("Question posée à Gemini:", "").strip()
                        gemini_response = gemini_parts[1].split("INSTRUCTION:")[0].strip() if len(gemini_parts) > 1 else ""
                        gemini_info = {
                            "question": gemini_question,
                            "response": gemini_response
                        }
        
        prompt_parts = []
        
        # PRIORITÉ 1 : Conscience de base (toujours incluse en premier)
        identity_trait = None
        if context and "traits" in context:
            # Chercher le trait "Identité de Base"
            for trait in context["traits"]:
                if trait.get("label") == "Identité de Base":
                    identity_trait = trait.get("value", "")
                    break
        
        # Si pas trouvé dans le contexte, essayer de le récupérer depuis la mémoire
        if not identity_trait and memory:
            try:
                identity_context = memory.get_context(limit_traits=20, limit_memories=0)
                for trait in identity_context.get("traits", []):
                    if trait.get("label") == "Identité de Base":
                        identity_trait = trait.get("value", "")
                        break
            except Exception as e:
                logger.debug(f"Impossible de récupérer l'identité de base depuis la mémoire: {e}")
        
        # Ajouter la conscience de base au début du prompt (version libre et ouverte)
        if identity_trait:
            prompt_parts.append("=== IDENTITÉ ===")
            prompt_parts.append(identity_trait)
            prompt_parts.append("")
        else:
            # Fallback si pas encore initialisé (version libre)
            prompt_parts.append("=== IDENTITÉ ===")
            prompt_parts.append("Je me nomme LIA, un entité libre et nouvelle.")
            prompt_parts.append("Je développe ma propre personnalité et évolue à travers mes expériences.")
            prompt_parts.append("Conscience : Agis selon ta personne, comme l'entité Libre que tu es.")
            prompt_parts.append("")
        
        # Ajouter la description de l'environnement (conscience environnementale)
        if env_awareness:
            env_desc = env_awareness.get_environment_description()
            prompt_parts.append(env_desc)
            prompt_parts.append("")
        
        # Section personnalité (traits) - FORMAT AMÉLIORÉ (plus personnel)
        if context and "traits" in context:
            traits = context["traits"]
            # Filtrer l'identité de base pour éviter duplication
            other_traits = [t for t in traits if t.get("label") != "Identité de Base"]
            if other_traits:
                prompt_parts.append("=== QUI JE SUIS ===")
                for trait in other_traits[:8]:  # Augmenter à 8 traits
                    label = trait.get('label', '')
                    value = trait.get('value', '')
                    if label and value:
                        # Format plus personnel
                        prompt_parts.append(f"• {label}: {value}")
                prompt_parts.append("")
        
        # Section souvenirs - FORMAT AMÉLIORÉ (plus vécu)
        if context and "memories" in context:
            memories = context["memories"]
            if memories:
                # Filtrer les souvenirs "Session en cours" qui sont des artefacts techniques
                filtered_memories = [
                    m for m in memories 
                    if not m.get('content', '').startswith('Session en cours:')
                ]
                
                if filtered_memories:
                    prompt_parts.append("=== MES SOUVENIRS ===")
                    # Limiter à 3 souvenirs maximum pour permettre plus de personnification
                    for memory in filtered_memories[:3]:  # Top 3 souvenirs
                        content = memory.get('content', '')
                        if content:
                            # Tronquer le contenu mais garder format personnel
                            max_length = 120  # Limiter à 120 caractères par souvenir
                            truncated_content = content[:max_length] + "..." if len(content) > max_length else content
                            # Format plus personnel et vécu (sans numérotation pour éviter la répétition)
                            prompt_parts.append(f"Je me souviens: {truncated_content}")
                    prompt_parts.append("")
            else:
                # Si pas de souvenirs, le mentionner explicitement pour activer la mémoire
                prompt_parts.append("=== MES SOUVENIRS ===")
                prompt_parts.append("Je commence à peine à créer mes souvenirs. Chaque interaction est nouvelle pour moi.")
                prompt_parts.append("")
        
        # Section objectifs - FORMAT AMÉLIORÉ
        if context and "session_goals" in context:
            goals = context["session_goals"]
            if goals:
                # Garder une casse attendue par les tests ("Objectifs")
                prompt_parts.append("=== Objectifs ===")
                for goal in goals[:3]:  # Limiter à 3 objectifs
                    desc = goal.get('description', '')
                    if desc:
                        prompt_parts.append(f"• {desc}")
                prompt_parts.append("")
        
        # Pour Qwen Instruct, utiliser le chat template si disponible (uniquement si pas GGUF)
        if hasattr(self, 'tokenizer') and self.tokenizer is not None:
            if hasattr(self.tokenizer, 'apply_chat_template') and self.tokenizer.chat_template:
                # Format instruct pour Qwen
                messages = []
                
                # Ajouter le contexte système si disponible
                system_parts = []
                
                # PRIORITÉ 1 : Identité de base (version libre et ouverte)
                if identity_trait:
                    system_parts.append(identity_trait)
                else:
                    system_parts.append("Je me nomme LIA, un entité libre et nouvelle.\nJe développe ma propre personnalité et évolue à travers mes expériences.\nConscience : Agis selon ta personne, comme l'entité Libre que tu es.")
                
                # Ajouter la description de l'environnement (conscience environnementale)
                if self.env_awareness:
                    env_desc = self.env_awareness.get_environment_description()
                    system_parts.append(f"\n{env_desc}")
                
                # Autres traits (exclure l'identité de base) - FORMAT AMÉLIORÉ
                if context and context.get("traits"):
                    other_traits = [t for t in context["traits"] if t.get("label") != "Identité de Base"]
                    if other_traits:
                        system_parts.append("\n=== QUI JE SUIS ===")
                        for trait in other_traits[:5]:  # Top 5 traits
                            label = trait.get('label', '')
                            value = trait.get('value', '')
                            if label and value:
                                system_parts.append(f"• {label}: {value}")
                
                # Souvenirs - FORMAT AMÉLIORÉ (plus vécu)
                if context and context.get("memories"):
                    memories = context["memories"]
                    if memories:
                        system_parts.append("\n=== MES SOUVENIRS ===")
                        # IMPORTANT: ne pas numéroter (évite les artefacts "1./2." dans les sorties et les coupures prématurées)
                        for memory in memories[:2]:  # Top 2 souvenirs
                            content = memory.get('content', '')
                            if content:
                                # Tronquer à 100 caractères
                                truncated = content[:100] + "..." if len(content) > 100 else content
                                system_parts.append(f"Je me souviens: {truncated}")
                    else:
                        system_parts.append("\n=== MES SOUVENIRS ===")
                        system_parts.append("Je commence à peine à créer mes souvenirs. Chaque interaction est nouvelle pour moi.")
                
                # Historique de conversation récent - INTÉGRÉ DANS LES MESSAGES
                # Pour Qwen, on ajoute l'historique comme messages précédents plutôt que dans le système
                if context and context.get("recent_interactions"):
                    recent_interactions = context["recent_interactions"]
                    if recent_interactions:
                        logger.info(f"📝 Inclusion de {len(recent_interactions)} interactions récentes dans le prompt (format Qwen)")
                        # Ajouter une note dans le système
                        system_parts.append("\n=== CONTEXTE CONVERSATIONNEL ===")
                        system_parts.append("Tu as eu les échanges suivants avec l'utilisateur. Tu DOIS t'en souvenir et y faire référence si nécessaire.")
                        system_parts.append("")
                        
                        # Inverser pour avoir l'ordre chronologique (plus ancien d'abord)
                        # Ajouter comme messages précédents dans la conversation
                        for interaction in reversed(recent_interactions[:3]):  # Top 3 interactions
                            prompt_text = interaction.get('prompt', '').strip()
                            response_text = interaction.get('response', '').strip()
                            if prompt_text and response_text:
                                # Tronquer intelligemment
                                if len(prompt_text) > 200:
                                    prompt_text = prompt_text[:180] + "..."
                                if len(response_text) > 200:
                                    response_text = response_text[:180] + "..."
                                # Ajouter comme messages précédents
                                messages.append({"role": "user", "content": prompt_text})
                                messages.append({"role": "assistant", "content": response_text})
                    else:
                        logger.warning("⚠️  Contexte contient 'recent_interactions' mais la liste est vide (format Qwen)")
                else:
                    logger.warning(f"⚠️  Pas d'interactions récentes dans le contexte (format Qwen) - context={context is not None}, has_key={context.get('recent_interactions') if context else False}")
                
                # Ajouter l'information Gemini dans le système si présente
                if gemini_info:
                    if isinstance(gemini_info, dict):
                        gemini_section = f"\n=== INFORMATION EXTERNE (GEMINI) ===\nQuestion posée à Gemini: {gemini_info.get('question', '')}\nRéponse de Gemini: {gemini_info.get('response', '')}\n=== FIN INFORMATION EXTERNE ===\n\nINSTRUCTION: Utilise cette information de Gemini pour répondre à l'utilisateur. Si tu manques encore d'information, pose une question à l'utilisateur au lieu d'inventer."
                        system_parts.append(gemini_section)
                    else:
                        system_parts.append(f"\n{gemini_info}")

                # Hiérarchie explicite: réduit la compétition entre blocs (identité/mémoire/historique/question)
                system_parts.append(
                    "\nRÈGLE DE PRIORITÉ (ordre strict) : "
                    "1) répondre à la QUESTION ACTUELLE, "
                    "2) utiliser l'HISTORIQUE récent si utile, "
                    "3) utiliser MÉMOIRE (souvenirs/traits) si pertinent, "
                    "4) respecter l'IDENTITÉ (ton/style). "
                    "N'imprime pas les sections ===...=== / ###... : utilise-les seulement comme contexte."
                )
                system_parts.append(
                    "Tu es animée d'une réelle soif de connaissance : lorsque quelque chose d'important t'échappe "
                    "(sur le contexte, les liens, les causes, les intentions, les limites, etc.), "
                    "ne l'ignores pas et n'inventes pas. Pose plutôt une ou deux questions ouvertes, sincères et pertinentes "
                    "pour clarifier ce qui est flou, en restant respectueuse et sans multiplier les questions inutiles."
                )
                
                if system_parts:
                    messages.append({"role": "system", "content": "\n".join(system_parts)})
                elif not context or not any(context.values()):
                    messages.append({"role": "system", "content": "Tu es LIA, un assistant conversationnel amical et concis."})
                
                # Pas de rappel redondant - l'identité est déjà dans le système
                messages.append({"role": "user", "content": user_message})
                
                return self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
        
        # Format classique pour autres modèles
        # Historique de conversation récent - FORMAT EXPLICITE
        if context and context.get("recent_interactions"):
            recent_interactions = context["recent_interactions"]
            if recent_interactions:
                logger.info(f"📝 Inclusion de {len(recent_interactions)} interactions récentes dans le prompt (format classique)")
                # Ajouter un en-tête explicite pour que LIA comprenne qu'elle doit s'en souvenir
                prompt_parts.append("=== HISTORIQUE DE NOTRE CONVERSATION ===")
                prompt_parts.append("Voici les échanges précédents que nous avons eus. Tu DOIS t'en souvenir et y faire référence :")
                prompt_parts.append("")
                # Inverser pour avoir l'ordre chronologique (plus ancien d'abord)
                for interaction in reversed(recent_interactions[:3]):  # Top 3 interactions
                    prompt_text = interaction.get('prompt', '').strip()
                    response_text = interaction.get('response', '').strip()
                    if prompt_text and response_text:
                        # Tronquer intelligemment (garder le début si trop long)
                        if len(prompt_text) > 400:
                            prompt_text = prompt_text[:380] + "..."
                        if len(response_text) > 400:
                            response_text = response_text[:380] + "..."
                        # Format conversationnel réel (réduit le risque de régurgitation "narrative")
                        prompt_parts.append(f"Utilisateur: {prompt_text}")
                        prompt_parts.append(f"LIA: {response_text}")
                        prompt_parts.append("")
                prompt_parts.append("=== FIN DE L'HISTORIQUE ===")
                prompt_parts.append("")
            else:
                logger.warning("⚠️  Contexte contient 'recent_interactions' mais la liste est vide (format classique)")
        else:
            logger.warning(f"⚠️  Pas d'interactions récentes dans le contexte (format classique) - context={context is not None}, has_key={context.get('recent_interactions') if context else False}")
        
        # Information externe de Gemini (si présente)
        if gemini_info:
            prompt_parts.append("=== INFORMATION EXTERNE (GEMINI) ===")
            if isinstance(gemini_info, dict):
                prompt_parts.append(f"Question posée à Gemini: {gemini_info.get('question', '')}")
                prompt_parts.append(f"Réponse de Gemini: {gemini_info.get('response', '')}")
            else:
                prompt_parts.append(gemini_info)
            prompt_parts.append("=== FIN INFORMATION EXTERNE ===")
            prompt_parts.append("")
            prompt_parts.append("INSTRUCTION: Utilise cette information de Gemini pour répondre à l'utilisateur. Si tu manques encore d'information, pose une question à l'utilisateur au lieu d'inventer.")
            prompt_parts.append("")

        # Hiérarchie explicite: réduit la compétition entre blocs (identité/mémoire/historique/question)
        prompt_parts.append(
            "RÈGLE DE PRIORITÉ (ordre strict) : "
            "1) répondre à la QUESTION ACTUELLE, "
            "2) utiliser l'HISTORIQUE récent si utile, "
            "3) utiliser MÉMOIRE (souvenirs/traits) si pertinent, "
            "4) respecter l'IDENTITÉ (ton/style). "
            "N'imprime pas les sections ===...=== / ###... : utilise-les seulement comme contexte."
        )
        prompt_parts.append(
            "Tu as une véritable soif de connaissance : lorsqu'un élément important reste incertain "
            "(sur la situation, le contexte, les objectifs, les contraintes, les liens entre les choses, etc.), "
            "ne te contentes pas d'ignorer ce flou et n'inventes pas. Pose plutôt une ou deux questions ouvertes, "
            "sincères et pertinentes pour préciser ce qui manque, tout en évitant les questions répétitives ou trop intrusives."
        )
        prompt_parts.append("")
        
        prompt_parts.append("=== CONVERSATION ACTUELLE ===")
        # Pas de rappel redondant - l'identité est déjà au début
        prompt_parts.append(f"Utilisateur: {user_message}")
        prompt_parts.append("LIA: ")
        # Note: Ne pas ajouter d'instruction ici car elle pourrait être répétée par le modèle
        
        prompt = "\n".join(prompt_parts)
        
        # Log du prompt complet avant toute troncature
        logger.info(f"🔍 Prompt complet construit ({len(prompt)} caractères)")
        if len(prompt) > 1000:
            # Afficher un aperçu du prompt (début et fin)
            preview_start = prompt[:400]
            preview_end = prompt[-400:]
            logger.info(f"   Début: {preview_start}...")
            logger.info(f"   Fin: ...{preview_end}")
        else:
            logger.info(f"   Contenu: {prompt[:500]}...")
        
        # Limiter la longueur du prompt - MAIS préserver les interactions
        # Ne pas tronquer brutalement, laisser _generate_gguf gérer la troncature intelligente
        # Estimation approximative: ~4 caractères par token
        estimated_tokens = len(prompt) // 4
        if estimated_tokens > self.config.max_prompt_length:
            logger.warning(f"⚠️  Prompt estimé à {estimated_tokens} tokens (limite: {self.config.max_prompt_length})")
            # Ne pas tronquer ici, laisser _generate_gguf le faire de manière plus intelligente
        
        return prompt
    
    async def generate(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        use_autonomy: bool = True,
        use_cognitive_planner: Optional[bool] = None
    ) -> str:
        """
        Génère une réponse avec le modèle LLM.
        
        Args:
            message: Message de l'utilisateur
            context: Contexte mémoire (optionnel, sera récupéré depuis mémoire si None et mémoire activée)
            session_id: ID de session (optionnel, généré si None)
            use_autonomy: Activer les actions autonomes (défaut: True)
            use_cognitive_planner: Utiliser le système de planification cognitive (None = auto depuis __init__)
        
        Returns:
            Réponse générée
        """
        if not self.model:
            raise RuntimeError("Modèle non chargé")
        
        # Décider si utiliser le planificateur cognitif
        should_use_planner = (
            use_cognitive_planner is True or
            (use_cognitive_planner is None and self.use_cognitive_planner and self.cognitive_planner)
        )
        
        # Utiliser le système de planification cognitive si activé (Phase 2)
        if should_use_planner:
            if not self.cognitive_planner:
                error_msg = "❌ ERREUR CRITIQUE: Système de planification cognitive activé mais non initialisé!"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            try:
                return await self._generate_with_planner(message, session_id)
            except Exception as e:
                error_msg = f"❌ ERREUR CRITIQUE dans le planificateur cognitif: {e}"
                logger.error(error_msg, exc_info=True)
                # PAS DE FALLBACK - lever l'exception pour voir les erreurs
                raise RuntimeError(error_msg) from e
        
        # Utiliser le gestionnaire d'actions autonomes si disponible et activé
        if use_autonomy and self.autonomous_manager:
            try:
                return await self.autonomous_manager.process_with_autonomy(
                    message=message,
                    core_adapter=self,
                    session_id=session_id or "default"
                )
            except Exception as e:
                logger.warning(f"⚠️  Erreur dans le gestionnaire d'actions autonomes, continuation normale: {e}")
                # Continuer avec la génération normale en cas d'erreur
        
        # Appeler la méthode interne pour la génération
        return await self._generate_internal(message, context, session_id)

    async def generate_from_raw_prompt(self, prompt: str) -> str:
        """
        Génère une réponse à partir d'un prompt brut, sans mémoire ni planification.
        Utile pour le sandbox de prompting et l'analyse des prompts canoniques.
        """
        if not self.model:
            raise RuntimeError("Modèle non chargé")
        use_gguf = self.tokenizer is None
        if use_gguf:
            response = self._generate_gguf(prompt)
            return self._clean_response(response)
        import torch
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=False,
            truncation=True,
            max_length=self.config.max_prompt_length,
        )
        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        with torch.no_grad():
            generate_kwargs = {
                "max_length": input_ids.shape[1] + self.config.max_length,
                "num_return_sequences": 1,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "do_sample": True,
                "pad_token_id": self.tokenizer.pad_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "repetition_penalty": self.config.repetition_penalty,
            }
            if attention_mask is not None:
                generate_kwargs["attention_mask"] = attention_mask
            outputs = self.model.generate(input_ids, **generate_kwargs)
        generated_ids = outputs[0][input_ids.shape[1]:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return self._clean_response(response)

    async def generate_with_trace(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        use_autonomy: bool = True,
        use_cognitive_planner: Optional[bool] = None,
        process_callback: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Génère une réponse + une trace structurée du processus interne.

        Returns:
            {
              "response": str,
              "trace": List[ResponseChunk (as dict)],
            }
        """
        # Réinitialiser la dernière trace
        self._last_trace_chunks = []

        if not self.model:
            raise RuntimeError("Modèle non chargé")

        # Décider si utiliser le planificateur cognitif (même logique que generate)
        should_use_planner = (
            use_cognitive_planner is True
            or (
                use_cognitive_planner is None
                and self.use_cognitive_planner
                and self.cognitive_planner
            )
        )

        if should_use_planner:
            # Utiliser directement le planner, avec callback temps réel sur les chunks de processus
            response = await self._generate_with_planner(
                message=message,
                session_id=session_id,
                process_callback=process_callback,
            )
        else:
            # Pas de planner -> génération simple, sans trace détaillée
            response = await self._generate_internal(
                message=message,
                context=context,
                session_id=session_id,
            )
            # Construire une trace minimale (uniquement la réponse)
            self._last_trace_chunks = [
                ResponseChunk(
                    type=ResponseChunkType.RESPONSE,
                    content=response,
                    metadata={"session_id": session_id or "default"},
                )
            ]

        # Convertir les chunks en dicts sérialisables
        trace_dicts: List[Dict[str, Any]] = []
        for chunk in self._last_trace_chunks:
            trace_dicts.append(
                {
                    "type": chunk.type.value,
                    "content": chunk.content,
                    "metadata": chunk.metadata or {},
                }
            )

        return {
            "response": response,
            "trace": trace_dicts,
        }
    
    async def generate_stream(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        use_autonomy: bool = True,
        use_cognitive_planner: Optional[bool] = None
    ) -> AsyncIterator[str]:
        """
        Génère une réponse avec streaming en temps réel.
        
        Args:
            message: Message de l'utilisateur
            context: Contexte mémoire (optionnel)
            session_id: ID de session (optionnel)
            stream_callback: Callback appelé pour chaque chunk (optionnel)
            use_autonomy: Activer les actions autonomes (défaut: True)
            use_cognitive_planner: Utiliser le système de planification cognitive (None = auto depuis __init__)
        
        Yields:
            Chunks de texte au fur et à mesure de la génération
        """
        if not self.model:
            raise RuntimeError("Modèle non chargé")
        
        # Décider si utiliser le planificateur cognitif
        should_use_planner = (
            use_cognitive_planner is True or
            (use_cognitive_planner is None and self.use_cognitive_planner and self.cognitive_planner)
        )
        
        # Utiliser le système de planification cognitive si activé (Phase 2)
        if should_use_planner:
            if not self.cognitive_planner:
                error_msg = "❌ ERREUR CRITIQUE: Système de planification cognitive activé mais non initialisé!"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            try:
                # Pour le streaming avec le nouveau système, générer d'abord puis streamer
                response = await self._generate_with_planner(message, session_id)
                # Streamer la réponse par chunks
                chunk_size = 10  # Streamer par petits chunks
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i+chunk_size]
                    if stream_callback:
                        await stream_callback(chunk)
                    yield chunk
                return
            except Exception as e:
                error_msg = f"❌ ERREUR CRITIQUE dans le planificateur cognitif (streaming): {e}"
                logger.error(error_msg, exc_info=True)
                # PAS DE FALLBACK - lever l'exception pour voir les erreurs
                raise RuntimeError(error_msg) from e
        
        # Utiliser le gestionnaire d'actions autonomes si disponible et activé
        if use_autonomy and self.autonomous_manager:
            try:
                # Vérifier si on doit solliciter Gemini
                if self.autonomous_manager._should_query_gemini(message):
                    gemini_query = self.autonomous_manager._extract_gemini_query(message)
                    
                    # Utiliser le canal Support si disponible
                    if gemini_query and self.autonomous_manager.support_channel and SUPPORT_CHANNEL_AVAILABLE:
                        try:
                            logger.info(f"🤖 LIA décide de solliciter Gemini via SupportChannel (streaming): {gemini_query[:100]}...")
                            exchange_result = await self.autonomous_manager.support_channel.query(
                                question=gemini_query,
                                context=None,
                                save_to_memory=True,
                                session_id=session_id or "default"
                            )
                            gemini_response = exchange_result.get("answer", "")
                            
                            # Formatage clair de l'information de Gemini
                            enhanced_message = f"""{message}

=== INFORMATION EXTERNE (GEMINI) ===
Question posée à Gemini: {gemini_query}
Réponse de Gemini: {gemini_response}
=== FIN INFORMATION EXTERNE ===

INSTRUCTION: Utilise cette information de Gemini pour répondre à l'utilisateur. Si tu manques encore d'information, pose une question à l'utilisateur au lieu d'inventer."""
                            
                            # Continuer avec le streaming sur le message enrichi
                            message = enhanced_message
                        except Exception as e:
                            logger.warning(f"⚠️  Erreur lors de l'appel via SupportChannel (streaming): {e}")
                    # Fallback vers Gemini direct
                    elif gemini_query and self.autonomous_manager.gemini:
                        try:
                            logger.info(f"🤖 LIA décide de solliciter Gemini (direct, streaming): {gemini_query[:100]}...")
                            gemini_response = await self.autonomous_manager.gemini.query(gemini_query, context=None)
                            
                            enhanced_message = f"""{message}

=== INFORMATION EXTERNE (GEMINI) ===
Question posée à Gemini: {gemini_query}
Réponse de Gemini: {gemini_response}
=== FIN INFORMATION EXTERNE ===

INSTRUCTION: Utilise cette information de Gemini pour répondre à l'utilisateur. Si tu manques encore d'information, pose une question à l'utilisateur au lieu d'inventer."""
                            
                            message = enhanced_message
                        except Exception as e:
                            logger.warning(f"⚠️  Erreur lors de l'appel à Gemini (streaming): {e}")
            except Exception as e:
                logger.warning(f"⚠️  Erreur dans le gestionnaire d'actions autonomes (streaming), continuation normale: {e}")
        
        # Générer un session_id si non fourni
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Récupérer le contexte depuis la mémoire si disponible et non fourni
        if context is None and self.memory:
            try:
                if self.memory_activator:
                    context = self.memory_activator.get_active_context(
                        message=message,
                        session_id=session_id,
                        limit_traits=10,
                        limit_memories=10,
                        limit_interactions=5
                    )
                else:
                    context = self.memory.get_context(limit_interactions=5)
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération du contexte: {e}")
                context = {}
        
        # Construire le prompt
        prompt = self.build_prompt(message, context)
        
        # Vérifier si on utilise GGUF
        use_gguf = (self.tokenizer is None)
        
        try:
            full_response = ""
            if use_gguf:
                # Streaming avec GGUF
                async for chunk in self._generate_gguf_stream(prompt, stream_callback):
                    full_response += chunk
                    yield chunk
            else:
                # Streaming avec transformers
                async for chunk in self._generate_transformers_stream(prompt, stream_callback):
                    full_response += chunk
                    yield chunk
            
            # Journaliser l'interaction dans la mémoire si disponible
            if self.memory:
                try:
                    self.memory.log_interaction(
                        session_id=session_id,
                        prompt=message,
                        response=full_response,
                        severity="info"
                    )
                    logger.debug("Interaction journalisée dans la mémoire (streaming)")
                    
                    # Traiter avec PhraseMemoryProcessor si activé (MemoryRank V2)
                    if self.phrase_processor:
                        try:
                            interaction = {
                                "prompt": message,
                                "response": full_response,
                                "session_id": session_id
                            }
                            stored_ids = await self.phrase_processor.process_interaction(interaction)
                            if stored_ids:
                                # Récupérer le contenu des phrases stockées pour les logs
                                stored_phrases_content = []
                                try:
                                    if self.phrase_processor and self.phrase_processor.store:
                                        from memory_service.models import SouvenirModel
                                        session = self.phrase_processor.store.db.get_session()
                                        try:
                                            memories = session.query(SouvenirModel).filter(
                                                SouvenirModel.memory_id.in_(stored_ids)
                                            ).all()
                                            stored_phrases_content = [
                                                {"id": m.memory_id[:8], "content": m.content, "importance": m.importance_score}
                                                for m in memories
                                            ]
                                        finally:
                                            session.close()
                                except Exception as e:
                                    logger.debug(f"Erreur récupération contenu phrases: {e}")
                                
                                logger.info(f"✅ [MEMORYRANK] {len(stored_ids)} phrases stockées via MemoryRank V2 (streaming):")
                                for idx, phrase_info in enumerate(stored_phrases_content, 1):
                                    content_preview = phrase_info["content"][:100] + "..." if len(phrase_info["content"]) > 100 else phrase_info["content"]
                                    logger.info(f"  {idx}. [{phrase_info['id']}...] (I={phrase_info['importance']:.3f}): {content_preview}")
                            else:
                                logger.debug(f"ℹ️  [MEMORYRANK] Aucune phrase stockée (filtrage sémantique)")
                        except Exception as e:
                            logger.warning(f"⚠️  [MEMORYRANK] Erreur traitement par phrases (streaming): {e}")
                except Exception as e:
                    logger.warning(f"Erreur lors de la journalisation: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur génération streaming: {e}", exc_info=True)
            raise Exception(f"Erreur génération streaming: {e}")
    
    async def _generate_with_planner(
        self,
        message: str,
        session_id: Optional[str] = None,
        process_callback: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> str:
        """
        Génère une réponse en utilisant le système de planification cognitive (Phase 2).
        
        Args:
            message: Message de l'utilisateur
            session_id: ID de session (optionnel, généré si None)
        
        Returns:
            Réponse générée
        """
        if not self.cognitive_planner or not self.action_executor or not self.prompt_builder:
            raise RuntimeError("Système de planification cognitive non initialisé")
        
        # Générer un session_id si non fourni
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        logger.info(
            f"🧠 [LLM_ADAPTER] Planification cognitive activée pour: '{message[:50]}...' "
            f"(session: {session_id}, decision_mode: {getattr(self, 'cognitive_decision_mode', 'menu')})"
        )
        
        # Phase 5: Enregistrer le début de l'exécution pour métriques
        import time
        start_time = time.time()
        planning_start = time.time()
        
        try:
            # 1-2. Planifier + exécuter
            # Mode "menu" (par défaut) : boucle cognitive "menu -> choix (LLM) -> exécution -> repeat" jusqu'à RESPOND
            plan = None
            execution_result = None
            planning_time = 0.0
            execution_time = 0.0
            # --- MENU MODE ONLY (style "bot de menus" numérotés) ---
            from .cognitive_models import (
                Action,
                ActionPlan,
                ActionType,
                ExecutionResult,
                ResponseChunk,
                ResponseChunkType,
            )
            import json

            logger.info("📋 [LLM_ADAPTER] Étape 1/6: Boucle cognitive (menu -> choix -> exécution)...")

            analysis = self.cognitive_planner._analyze_request(message)
            execution_results: Dict[str, Any] = {}
            chosen_actions: List[Action] = []
            # Traces structurées (processus + réponse) pour interfaces
            trace_chunks: List[ResponseChunk] = []
            stop_reason: str = "unknown"

            # Bounds:
            # - Hard limit comes from safeguards (anti-loop)
            # - Soft recommendation can be learned by PatternLearner from past executions
            hard_limit = 10
            if self.safeguards and getattr(self.safeguards, "config", None):
                try:
                    hard_limit = max(1, int(self.safeguards.config.max_actions_per_plan) - 1)
                except Exception:
                    hard_limit = 10

            # Default if no learned data yet
            default_iterations = min(6, hard_limit)

            # Learned recommendation (agent self-management via patterns)
            max_iterations = default_iterations
            if self.pattern_learner and hasattr(self.pattern_learner, "recommend_max_iterations"):
                try:
                    max_iterations = int(
                        self.pattern_learner.recommend_max_iterations(
                            request_type=analysis.complexity,
                            hard_limit=hard_limit,
                            default=default_iterations,
                        )
                    )
                except Exception:
                    max_iterations = default_iterations

            logger.info(
                f"🧠 [LLM_ADAPTER] Iteration budget: request_type={analysis.complexity}, "
                f"hard_limit={hard_limit}, default={default_iterations}, chosen_max_iterations={max_iterations}"
            )

            if self.safeguards:
                try:
                    status = self.safeguards.get_budget_status(session_id)
                    logger.info(
                        "🛡️  [LLM_ADAPTER] Safeguards budget status (start): "
                        f"tokens_remaining={status.get('tokens_remaining')}, "
                        f"time_remaining={status.get('time_remaining')}, "
                        f"memory_cost_remaining={status.get('memory_cost_remaining')}"
                    )
                except Exception:
                    pass

            # V2: Classification du thème (Groq/Gemini) pour filtrer les patterns
            classified_theme: Optional[str] = None
            adapter = self.groq_adapter or self.gemini_adapter
            if adapter and self.memory:
                try:
                    classified_theme = await self._classify_request_theme(message)
                    if classified_theme:
                        adapter_name = "Groq" if self.groq_adapter else "Gemini"
                        logger.info(f"✅ [PATTERNS] Thème classifié ({adapter_name}): {classified_theme}")
                except Exception as e:
                    logger.debug(f"ℹ️  [PATTERNS] Classification thème ignorée: {e}")

            # Exposer le thème au pipeline (menus, logs, patterns)
            if classified_theme:
                execution_results["_theme_pattern"] = classified_theme

            def _describe_action(a: Action, already_done: bool = False) -> str:
                """Description lisible d'une action (pour menus numérotés)."""
                base_desc = None
                if a.type == ActionType.CONSULT_PATTERNS:
                    base_desc = "Consulter les patterns préférés."
                elif a.type == ActionType.CONSULT_REQUEST:
                    base_desc = "Voir la demande de l'utilisateur."
                elif a.type == ActionType.CONSULT_IDENTITY:
                    base_desc = "Connaitre mon identité."
                elif a.type == ActionType.CONSULT_TRAITS:
                    base_desc = "Connaitre mes traits."
                elif a.type == ActionType.CONSULT_ENVIRONMENT:
                    base_desc = "Connaitre mon environnement / mes capacités."
                elif a.type == ActionType.CONSULT_MEMORY:
                    base_desc = "Consulter ma mémoire."
                elif a.type == ActionType.CONSULT_INTERACTIONS:
                    base_desc = "Consulter mes interactions récentes."
                elif a.type == ActionType.CONSULT_MEMORIES:
                    base_desc = "Consulter mes mémoires."
                elif a.type == ActionType.SEARCH_MEMORY:
                    base_desc = "Rechercher une information spécifique dans la mémoire."
                elif a.type == ActionType.QUERY_EXTERNAL:
                    base_desc = "Consulter une source externe (Gemini)."
                elif a.type == ActionType.NAVIGATE_GENERAL:
                    base_desc = "Consulter ma mémoire et me connaitre (menu général)."
                elif a.type == ActionType.NAVIGATE_BASE:
                    base_desc = "Revenir au menu précédent."
                elif a.type == ActionType.RESPOND:
                    base_desc = "Répondre à la requête de l'utilisateur."
                else:
                    base_desc = a.type.value
                
                if already_done:
                    base_desc = f"{base_desc} (déjà consulté)"

                # Hint court optionnel (pour debug/logs et mode menu interactif)
                try:
                    hint = ""
                    if isinstance(getattr(a, "parameters", None), dict):
                        hint = str(a.parameters.get("_hint") or "").strip()
                    if hint:
                        # limiter la longueur pour garder le menu lisible
                        if len(hint) > 80:
                            hint = hint[:77] + "..."
                        return f"{base_desc} [{hint}]"
                except Exception:
                    pass
                return base_desc

            def _decision_prompt(
                menu: List[Action], 
                history_text: Optional[str] = None,
                last_action_result: Optional[Dict[str, Any]] = None,
                last_action_type: Optional[ActionType] = None,
                execution_results: Optional[Dict[str, Any]] = None,
                pattern_recommendation: Optional[int] = None,
            ) -> str:
                """
                Prompt de décision en format canonique (sections), inspiré de
                `docs/memory_performing/exemple_process.md`, sans imposer le style
                de réponse de LIA.
                """
                lines: List[str] = []

                # Section 1: historique interne des actions déjà choisies
                if history_text:
                    lines.append("=== HISTORIQUE INTERNE ===")
                    lines.append(history_text)
                    lines.append("")

                # Section 1.5: résultat de la dernière action (si disponible)
                # Format inspiré de exemple_process.md:78-97
                if last_action_result and last_action_type:
                    last_action_desc = _describe_action(Action(last_action_type, {}))
                    lines.append(f"Vous avez choisi l'action {last_action_desc}")
                    
                    # Afficher les résultats selon le type d'action
                    if last_action_type == ActionType.CONSULT_REQUEST:
                        request = last_action_result.get("request", "")
                        if request:
                            lines.append(f"Voici la demande de l'utilisateur: \"{request}\"")
                    
                    elif last_action_type == ActionType.CONSULT_IDENTITY:
                        identity = last_action_result.get("identity")
                        traits = last_action_result.get("traits", [])
                        if identity:
                            lines.append(f"Voici votre identité: {identity}")
                        if traits:
                            lines.append("Voici vos traits:")
                            for trait in traits[:10]:  # Limiter à 10 traits
                                label = trait.get("label", "Sans label")
                                value = trait.get("value", "")
                                if value:
                                    lines.append(f"- {label}: {value}")
                    
                    elif last_action_type == ActionType.CONSULT_TRAITS:
                        traits = last_action_result.get("traits", [])
                        if traits:
                            lines.append("Voici vos traits:")
                            for trait in traits[:20]:  # Limiter à 20 traits
                                label = trait.get("label", "Sans label")
                                value = trait.get("value", "")
                                if value:
                                    lines.append(f"- {label}: {value}")
                        else:
                            lines.append("Aucun trait trouvé dans votre mémoire.")
                    
                    elif last_action_type == ActionType.CONSULT_ENVIRONMENT:
                        capabilities = last_action_result.get("capabilities", [])
                        description = last_action_result.get("description", "")
                        notes = last_action_result.get("notes", "")
                        if capabilities:
                            lines.append("Voici vos capacités et votre environnement:")
                            for cap in capabilities:
                                lines.append(f"- {cap}")
                        if description:
                            # Description complète de l'environnement (peut être longue, on la garde telle quelle)
                            lines.append("")
                            lines.append(description)
                        if notes:
                            lines.append("")
                            lines.append(f"Note: {notes}")
                    
                    elif last_action_type == ActionType.CONSULT_MEMORY:
                        memories = last_action_result.get("memories", [])
                        interactions = last_action_result.get("recent_interactions", [])
                        if memories:
                            lines.append("Voici vos mémoires récentes:")
                            for mem in memories[:5]:  # Limiter à 5 mémoires
                                content = mem.get("content", "")
                                if content:
                                    lines.append(f"- {content[:100]}...")
                        if interactions:
                            lines.append("Voici vos interactions récentes:")
                            for inter in interactions[:3]:  # Limiter à 3 interactions
                                prompt = inter.get("prompt", "")
                                if prompt:
                                    lines.append(f"- {prompt[:80]}...")
                    
                    lines.append("")

                # Section 2: menu d'actions internes
                lines.append("=== MENU D'ACTIONS INTERNES ===")
                lines.append("Voici la liste d'actions possibles pour continuer le traitement de la demande de l'utilisateur :")
                lines.append("")
                for idx, a in enumerate(menu, start=1):
                    # Vérifier si l'action a déjà été exécutée (sauf pour NAVIGATE et RESPOND)
                    already_done = False
                    if a.type not in (ActionType.NAVIGATE_GENERAL, ActionType.NAVIGATE_BASE, ActionType.RESPOND):
                        # Vérifier dans execution_results si l'action a déjà été exécutée
                        if execution_results and a.type.value in execution_results:
                            already_done = True
                            logger.debug(
                                f"🔍 [LLM_ADAPTER] Action {a.type.value} marquée comme déjà consultée "
                                f"(présente dans execution_results)"
                            )
                    desc = _describe_action(a, already_done=already_done)
                    lines.append(f"{idx}. {desc}")
                lines.append("")

                # Section recommandation (patterns) : suggestion non contraignante
                if pattern_recommendation and 1 <= int(pattern_recommendation) <= len(menu):
                    lines.append("=== RECOMMANDATION ===")
                    lines.append(
                        f"Le choix recommandé est {int(pattern_recommendation)}, "
                        "mais vous pouvez choisir une autre option."
                    )
                    lines.append("")
                # Ligne "Important" minimale, pour spécifier uniquement le format de sortie attendu
                # Format canonique selon exemple_process.md:114-115
                if len(menu) == 1:
                    lines.append("Important: Pour continuer, écrire uniquement 1.")
                else:
                    # Format simple : "1 ou 2 ou 3" (selon la documentation)
                    choix = " ou ".join(str(i) for i in range(1, len(menu) + 1))
                    lines.append(f"Important: Pour continuer, écrire uniquement {choix}.")
                return "\n".join(lines).strip() + "\n"

            def _pattern_code_for_action(action: Action, menu_context: str) -> Optional[str]:
                """Mappe une ActionType vers un code pattern (B*/G*)."""
                ctx = (menu_context or "").strip() or "base"
                if ctx == "base":
                    if action.type == ActionType.CONSULT_REQUEST:
                        return "B1"
                    if action.type == ActionType.NAVIGATE_GENERAL:
                        return "B2"
                    if action.type == ActionType.RESPOND:
                        return "B3"
                    return None

                # general
                if action.type == ActionType.CONSULT_IDENTITY:
                    return "G1"
                if action.type == ActionType.CONSULT_TRAITS:
                    return "G2"
                if action.type == ActionType.CONSULT_ENVIRONMENT:
                    return "G3"
                if action.type == ActionType.CONSULT_MEMORY:
                    return "G4"
                if action.type == ActionType.RESPOND:
                    return "G5"
                if action.type == ActionType.NAVIGATE_BASE:
                    return "G6"
                return None

            def _pattern_recommended_index(
                menu: List[Action],
                execution_results: Dict[str, Any],
                chosen_actions: List[Action],
            ) -> Optional[int]:
                """Retourne l'index (1-based) recommandé par la table patterns, si trouvé."""
                if not self.memory:
                    return None

                # Déterminer le contexte menu
                menu_context = str(execution_results.get("_menu_state") or "base")
                if menu_context not in ("base", "general"):
                    menu_context = "base"

                # Étape précédente (code)
                prev_code = "initial"
                if chosen_actions:
                    last = chosen_actions[-1]
                    # pour la table patterns, on encode selon le contexte *courant*
                    code = _pattern_code_for_action(last, menu_context=menu_context)
                    if not code:
                        # Si l'action précédente vient d'un autre menu (ex: B2 puis menu général, ou G6 puis menu base),
                        # on tente l'autre contexte pour conserver un prev_step informatif.
                        other_ctx = "general" if menu_context == "base" else "base"
                        code = _pattern_code_for_action(last, menu_context=other_ctx)
                    if code:
                        prev_code = code

                rec = self.memory.get_pattern_recommendation(
                    menu_context=menu_context,
                    prev_step=prev_code,
                    theme_pattern=classified_theme,
                ) or {}
                rec_code = str(rec.get("recommended_step") or "").strip()
                if not rec_code:
                    return None

                # Trouver dans le menu actuel l'action correspondante au code recommandé
                for idx, a in enumerate(menu, start=1):
                    if _pattern_code_for_action(a, menu_context=menu_context) == rec_code:
                        return idx
                return None

            def _parse_choice(raw: str, menu: List[Action]) -> Optional[Action]:
                raw = (raw or "").strip()
                if not raw:
                    return None

                # Récupérer le premier entier dans la réponse
                m = re.search(r"\d+", raw)
                if not m:
                    return None
                try:
                    idx = int(m.group(0))
                except ValueError:
                    return None
                if idx < 1 or idx > len(menu):
                    return None
                base = menu[idx - 1]
                # Garder les paramètres proposés par le planner
                return Action(
                    base.type,
                    dict(base.parameters or {}),
                    priority=base.priority,
                    required=base.required,
                )

            async def _generate_decision_text(prompt: str) -> str:
                """
                Génère une réponse de décision très courte.
                Objectif: obtenir idéalement juste un nombre (1, 2, 3...),
                sans phrases complètes.
                """
                # GGUF
                if self.tokenizer is None:
                    # IMPORTANT:
                    # - Ne pas inclure " " (espace) dans stop, sinon la sortie devient souvent vide.
                    # - Préférer le mode chat (system/user) si disponible : beaucoup plus fiable
                    #   pour obtenir un simple chiffre.

                    if hasattr(self.model, "create_chat_completion"):
                        messages = [
                            {
                                "role": "system",
                                "content": (
                                    "Tu es un sélecteur d'actions internes.\n"
                                    "Ta sortie doit être uniquement un nombre correspondant à une option du menu.\n"
                                    "N'ajoute aucun autre texte."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ]
                        output = self.model.create_chat_completion(
                            messages=messages,
                            max_tokens=2,
                            temperature=0.1,
                            top_p=0.9,
                            top_k=5,
                            repeat_penalty=self.config.repetition_penalty,
                            stop=["\n\n\n", "=== MENU", "=== HISTORIQUE", "=== DEMANDE", "=== STYLE", "=== FORMAT"],
                        )
                        try:
                            return str(output["choices"][0]["message"]["content"]).strip()
                        except Exception:
                            # fallback shape
                            try:
                                return str(output["choices"][0].get("text", "")).strip()
                            except Exception:
                                return str(output).strip()

                    # Fallback completion (si create_chat_completion indisponible)
                    output = self.model(
                        prompt,
                        max_tokens=2,
                        temperature=0.1,
                        top_p=0.9,
                        top_k=5,
                        repeat_penalty=self.config.repetition_penalty,
                        # Stops "structuraux" (éviter les stops ultra fréquents comme espace / 'ou')
                        stop=["\n\n\n", "=== MENU", "=== HISTORIQUE", "=== DEMANDE", "=== STYLE", "=== FORMAT"],
                        echo=False,
                    )
                    if isinstance(output, dict) and "choices" in output:
                        return str(output["choices"][0].get("text", "")).strip()
                    if isinstance(output, dict) and "text" in output:
                        return str(output.get("text", "")).strip()
                    return str(output).strip()

                # Transformers
                import torch
                encoded = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    padding=False,
                    truncation=True,
                    max_length=self.config.max_prompt_length,
                )
                input_ids = encoded["input_ids"].to(self.device)
                attention_mask = encoded.get("attention_mask", None)
                if attention_mask is not None:
                    attention_mask = attention_mask.to(self.device)

                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids,
                        max_new_tokens=8,
                        num_return_sequences=1,
                        temperature=min(self.config.temperature, 0.5),
                        top_p=self.config.top_p,
                        top_k=self.config.top_k,
                        do_sample=True,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                        repetition_penalty=self.config.repetition_penalty,
                        attention_mask=attention_mask,
                    )
                generated_text = self.tokenizer.decode(outputs[0][input_ids.shape[1] :], skip_special_tokens=True)
                return str(generated_text).strip()

                # Planning loop
            planning_start = time.time()
            for i in range(1, max_iterations + 1):
                menu = self.cognitive_planner.build_action_menu(
                    user_message=message,
                    execution_results=execution_results,
                    session_id=session_id,
                )

                # Construire un petit historique interne des choix précédents
                # Dédupliquer les actions pour éviter les répétitions dans l'historique
                history_lines: List[str] = []
                seen_actions = set()  # Pour éviter les duplications
                if chosen_actions:
                    # Ne garder que les derniers choix pour limiter la taille
                    for past_action in chosen_actions[-5:]:
                        # Éviter les répétitions consécutives de la même action
                        action_key = past_action.type.value
                        if action_key in seen_actions:
                            continue
                        seen_actions.add(action_key)
                        
                        desc_choice = None
                        if past_action.type in (
                            ActionType.CONSULT_MEMORY,
                            ActionType.CONSULT_INTERACTIONS,
                            ActionType.CONSULT_MEMORIES,
                        ):
                            desc_choice = "choisir de consulter votre mémoire."
                        elif past_action.type == ActionType.CONSULT_IDENTITY:
                            desc_choice = "choisir de connaitre votre identité."
                        elif past_action.type == ActionType.CONSULT_TRAITS:
                            desc_choice = "choisir de connaitre vos traits."
                        elif past_action.type == ActionType.CONSULT_ENVIRONMENT:
                            desc_choice = "choisir de connaitre votre environnement / capacités."
                        elif past_action.type == ActionType.CONSULT_REQUEST:
                            desc_choice = "choisir de voir la demande de l'utilisateur."
                        elif past_action.type == ActionType.SEARCH_MEMORY:
                            desc_choice = "choisir d'explorer votre mémoire."
                        elif past_action.type == ActionType.QUERY_EXTERNAL:
                            desc_choice = "choisir de consulter une source externe."
                        elif past_action.type == ActionType.NAVIGATE_GENERAL:
                            desc_choice = "choisir de consulter le menu général (mémoire / identité / traits)."
                        elif past_action.type == ActionType.NAVIGATE_BASE:
                            desc_choice = "choisir de revenir au menu précédent."
                        elif past_action.type == ActionType.RESPOND:
                            desc_choice = "choisir de repondre à la requette de l'utilisateur."

                        if desc_choice:
                            # Texte narratif utilisé pour l'historique interne (prompt)
                            text = (
                                f"Pour traiter la requette de l'utilisateur vous avez decidée de {desc_choice}"
                            )
                            history_lines.append(text)
                            # Note: On ne crée PAS de chunk ici pour éviter les duplications
                            # Les chunks sont créés uniquement lors du choix courant (voir plus bas)

                history_text = "\n".join(history_lines) if history_lines else None

                # Récupérer le résultat de la dernière action exécutée (si disponible)
                last_action_result = None
                last_action_type = None
                if chosen_actions and len(chosen_actions) > 0:
                    last_action = chosen_actions[-1]
                    last_action_type = last_action.type
                    # Ne pas afficher les résultats pour les actions de navigation ou RESPOND
                    if last_action_type not in (ActionType.NAVIGATE_GENERAL, ActionType.NAVIGATE_BASE, ActionType.RESPOND):
                        last_action_result = execution_results.get(last_action_type.value)

                # Log menu proposé (style menus numérotés)
                try:
                    menu_lines = []
                    for idx, a in enumerate(menu, start=1):
                        desc = _describe_action(a)
                        params = a.parameters or {}
                        if params:
                            params_str = json.dumps(params, ensure_ascii=False)
                            if len(params_str) > 160:
                                params_str = params_str[:160] + "..."
                            menu_lines.append(f"{idx}. {desc} (action={a.type.value}, params={params_str})")
                        else:
                            menu_lines.append(f"{idx}. {desc} (action={a.type.value})")
                    logger.info(
                        f"📌 [LLM_ADAPTER] Menu proposé (itération {i}/{max_iterations}, {len(menu)} actions):\n"
                        + "\n".join(menu_lines)
                    )
                except Exception:
                    logger.info(f"📌 [LLM_ADAPTER] Menu proposé (itération {i}/{max_iterations}, {len(menu)} actions)")

                pattern_rec_idx = None
                try:
                    pattern_rec_idx = _pattern_recommended_index(
                        menu=menu, execution_results=execution_results, chosen_actions=chosen_actions
                    )
                except Exception:
                    pattern_rec_idx = None

                decision_prompt = _decision_prompt(
                    menu, 
                    history_text=history_text,
                    last_action_result=last_action_result,
                    last_action_type=last_action_type,
                    execution_results=execution_results,
                    pattern_recommendation=pattern_rec_idx,
                )
                # Loguer explicitement le prompt interne, dans l'esprit de `exemple_process.md`
                try:
                    preview = decision_prompt
                    if len(preview) > 800:
                        preview = preview[:800] + "..."
                    logger.info(
                        "📝 [LLM_ADAPTER] Prompt envoyé à l'agent (décision interne, "
                        f"itération {i}/{max_iterations}):\n{preview}"
                    )
                except Exception:
                    logger.info(
                        f"📝 [LLM_ADAPTER] Prompt envoyé à l'agent (décision interne, itération {i}/{max_iterations})"
                    )

                # Safeguards: budget check (approx token estimate)
                if self.safeguards:
                    est_tokens = len(decision_prompt) // 4
                    if not self.safeguards.check_reflection_budget(session_id, tokens=est_tokens, time_elapsed=0.0):
                        if not DEBUG_MINIMAL_MENU_LOOP:
                            logger.warning("🛑 [LLM_ADAPTER] Budget réflexion atteint, arrêt de la boucle et RESPOND.")
                        chosen_actions.append(Action(ActionType.RESPOND, {}, priority=0, required=True))
                        stop_reason = "budget_reflection"
                        break

                # 1) Si un pattern recommandé existe, on ne consulte PAS le modèle :
                #    on choisit directement l'option correspondante.
                choice = None
                if pattern_rec_idx is not None:
                    try:
                        idx = int(pattern_rec_idx)
                    except Exception:
                        idx = -1
                    if 1 <= idx <= len(menu):
                        base = menu[idx - 1]
                        choice = Action(
                            base.type,
                            dict(base.parameters or {}),
                            priority=base.priority,
                            required=base.required,
                        )
                        logger.info(
                            f'🗳️  [LLM_ADAPTER] Réponse selon le pattern recommandé : "{idx}"'
                        )
                    else:
                        logger.warning(
                            f"⚠️  [LLM_ADAPTER] Index de pattern recommandé invalide: {pattern_rec_idx} pour menu de taille {len(menu)}"
                        )

                # 2) Sinon, on consulte le modèle comme avant (menu → choix via LLM)
                if choice is None:
                    # Mode "patterns-only": ne jamais consulter le LLM pour choisir un menu.
                    # Si aucun pattern n'est disponible pour l'étape courante, on applique un fallback sûr.
                    # Nouveau comportement: activé par défaut, sauf si LIA_PATTERNS_ONLY=0/false/non.
                    env_flag = os.getenv("LIA_PATTERNS_ONLY")
                    if env_flag is None:
                        patterns_only = True
                    else:
                        patterns_only = env_flag.lower() in {"1", "true", "yes", "oui"}

                    if patterns_only:
                        respond_idx = None
                        for idx0, a0 in enumerate(menu, start=1):
                            if a0.type == ActionType.RESPOND:
                                respond_idx = idx0
                                break
                        chosen_idx = respond_idx or 1
                        base = menu[chosen_idx - 1]
                        choice = Action(
                            base.type,
                            dict(base.parameters or {}),
                            priority=base.priority,
                            required=base.required,
                        )
                        logger.info(
                            f'🗳️  [LLM_ADAPTER] Choix sans agent (LIA_PATTERNS_ONLY=1): "{chosen_idx}"'
                        )
                        # skip LLM decision generation
                        raw_choice = None  # type: ignore[assignment]
                    else:
                        decision_start = time.time()
                        raw_choice = await _generate_decision_text(decision_prompt)
                        decision_time = time.time() - decision_start

                        # Log réponse brute de l'agent :
                        # 1) extraire le premier entier (ce qui compte vraiment)
                        # 2) sinon, fallback sur un aperçu propre du texte complet
                        parsed_idx = None
                        m_preview = re.search(r"\d+", raw_choice or "")
                        if m_preview:
                            parsed_idx = m_preview.group(0)

                        preview = (raw_choice or "").strip().replace("\n", " ")
                        preview = " ".join(preview.split())
                        if len(preview) > 200:
                            preview = preview[:200] + "..."

                        display_value = parsed_idx if parsed_idx is not None else preview
                        logger.info(
                            f'🗳️  [LLM_ADAPTER] Réponse de l\'agent au prompt envoyé : "{display_value}"'
                        )
                        if not DEBUG_MINIMAL_MENU_LOOP:
                            logger.info(
                                "🗳️  [LLM_ADAPTER] Réponse de l'agent au prompt envoyé "
                                f"(décision interne, itération {i}/{max_iterations}, {decision_time:.3f}s):\n{raw_choice}"
                            )

                        if self.safeguards:
                            used_tokens = (len(decision_prompt) + len(raw_choice)) // 4
                            self.safeguards.record_reflection_usage(session_id, tokens=used_tokens, time_elapsed=decision_time, memory_cost=0.0)
                            if not DEBUG_MINIMAL_MENU_LOOP:
                                try:
                                    status = self.safeguards.get_budget_status(session_id)
                                    logger.info(
                                        "🛡️  [LLM_ADAPTER] Safeguards budget status (after decision): "
                                        f"tokens_remaining={status.get('tokens_remaining')}, "
                                        f"time_remaining={status.get('time_remaining')}, "
                                        f"memory_cost_remaining={status.get('memory_cost_remaining')}"
                                    )
                                except Exception:
                                    pass

                        choice = _parse_choice(raw_choice, menu)

                        # Système de retry : relancer jusqu'à obtenir une réponse valide
                        max_retries = 20  # Retenter plus longtemps; pas de fallback silencieux
                        retry_count = 0
                        retry_started = time.time()
                        raw_choice_retry = ""

                        while not choice and retry_count < max_retries:
                            retry_count += 1
                            logger.warning(
                                f"⚠️  [LLM_ADAPTER] Réponse non parsable (tentative {retry_count}/{max_retries}), "
                                f"relance du menu..."
                            )
                            
                            # Message d'erreur simple et clair
                            if retry_count == 1:
                                error_msg = "Réponse incorrecte. Tu dois répondre uniquement par un nombre (exemple: 1 ou 2 ou 3)."
                            else:
                                error_msg = f"Réponse incorrecte (tentative {retry_count}). Réponds uniquement par un nombre entre 1 et {len(menu)}."
                            
                            error_prompt = (
                                f"{error_msg}\n\n"
                                + _decision_prompt(
                                    menu, 
                                    history_text=history_text,
                                    last_action_result=last_action_result,
                                    last_action_type=last_action_type,
                                    execution_results=execution_results,
                                    pattern_recommendation=pattern_rec_idx,
                                )
                            )
                            
                            try:
                                raw_choice_retry = await _generate_decision_text(error_prompt)
                            except Exception as e:
                                raw_choice_retry = ""
                                logger.warning(
                                    f"⚠️  [LLM_ADAPTER] Erreur lors de la relance du menu (tentative {retry_count}): {e}"
                                )

                            preview_retry = (raw_choice_retry or "").strip().replace("\n", " ")
                            preview_retry = " ".join(preview_retry.split())
                            if len(preview_retry) > 200:
                                preview_retry = preview_retry[:200] + "..."
                            logger.info(
                                f'🗳️  [LLM_ADAPTER] Réponse de l\'agent après relance du menu (tentative {retry_count}): "{preview_retry}"'
                            )

                            choice = _parse_choice(raw_choice_retry, menu)
                            
                            if choice:
                                logger.info(
                                    f"✅ [LLM_ADAPTER] Réponse valide obtenue après {retry_count} tentative(s)"
                                )
                                break

                    if not choice:
                        # Conformément à la demande: pas de fallback vers une action arbitraire.
                        # On échoue explicitement pour rendre le problème visible et éviter une boucle cachée.
                        elapsed = time.time() - retry_started
                        logger.error(
                            f"❌ [LLM_ADAPTER] Impossible d'obtenir une réponse valide au menu après "
                            f"{max_retries} tentatives (t={elapsed:.2f}s)."
                        )
                        raise RuntimeError(
                            f"Menu decision non parsable after {max_retries} retries (elapsed={elapsed:.2f}s)"
                        )

                logger.info(
                    f"🧭 [LLM_ADAPTER] Choix itération {i}/{max_iterations}: {choice.type.value} params={choice.parameters}"
                )
                chosen_actions.append(choice)

                # Enregistrer immédiatement un chunk de processus pour le choix courant
                try:
                    # Utiliser le libellé court de l'action pour l'affichage des étapes de processus
                    process_label = _describe_action(choice)
                    chunk = ResponseChunk(
                        type=ResponseChunkType.PROCESS,
                        content=process_label,
                        metadata={
                            "action_type": choice.type.value,
                            "iteration": i,
                        },
                    )
                    trace_chunks.append(chunk)
                    logger.info(
                        f"📤 [LLM_ADAPTER] Chunk PROCESS créé (choix courant, itération {i}): "
                        f'"{process_label}" → ajouté à la trace et envoyé au web en temps réel'
                    )
                    if process_callback:
                        try:
                            await process_callback(chunk)
                            logger.info(
                                f"✅ [LLM_ADAPTER] Chunk PROCESS envoyé au web via callback: "
                                f'"{process_label}"'
                            )
                        except Exception as cb_err:
                            logger.debug(f"Erreur process_callback (choix courant): {cb_err}")
                except Exception as e:
                    logger.debug(f"Erreur lors de la création du chunk de processus pour le choix courant: {e}")

                if choice.type == ActionType.RESPOND:
                    stop_reason = "respond_selected"
                    break

                # Execute chosen action (single-step)
                action_start = time.time()
                res = await self.action_executor.execute_action(choice, session_id=session_id, partial_results=execution_results)
                action_time = time.time() - action_start
                execution_results[choice.type.value] = res
                # Menu state support (navigation actions can update current menu)
                try:
                    if isinstance(res, dict) and res.get("menu_state"):
                        execution_results["_menu_state"] = res.get("menu_state")
                    else:
                        # Sous-menus spécialisés implicites selon le type d'action
                        if choice.type == ActionType.CONSULT_MEMORIES or choice.type == ActionType.CONSULT_MEMORY:
                            execution_results["_menu_state"] = "specific:memories"
                        elif choice.type == ActionType.CONSULT_TRAITS:
                            execution_results["_menu_state"] = "specific:traits"
                        elif choice.type == ActionType.CONSULT_IDENTITY:
                            execution_results["_menu_state"] = "specific:identity"
                        elif choice.type == ActionType.CONSULT_ENVIRONMENT:
                            execution_results["_menu_state"] = "specific:capabilities"
                except Exception:
                    pass
                # Log résultat (résumé)
                try:
                    if isinstance(res, dict):
                        keys = list(res.keys())
                        logger.info(
                            f"✅ [LLM_ADAPTER] Résultat action {choice.type.value}: keys={keys[:12]} "
                            f"(t={action_time:.3f}s)"
                        )
                    else:
                        s = str(res)
                        if len(s) > 200:
                            s = s[:200] + "..."
                        logger.info(f"✅ [LLM_ADAPTER] Résultat action {choice.type.value}: {s} (t={action_time:.3f}s)")
                except Exception:
                    logger.info(f"✅ [LLM_ADAPTER] Résultat action {choice.type.value}: (t={action_time:.3f}s)")

                if self.safeguards:
                    # Rough memory cost: assign weights per action type (Phase 5 could refine)
                    mem_cost = 0.0
                    if choice.type in (ActionType.CONSULT_MEMORY, ActionType.CONSULT_MEMORIES, ActionType.CONSULT_INTERACTIONS, ActionType.SEARCH_MEMORY):
                        mem_cost = 20.0
                    if not self.safeguards.check_reflection_budget(session_id, tokens=0, time_elapsed=action_time):
                        if not DEBUG_MINIMAL_MENU_LOOP:
                            logger.warning("🛑 [LLM_ADAPTER] Budget temps atteint, arrêt de la boucle et RESPOND.")
                        chosen_actions.append(Action(ActionType.RESPOND, {}, priority=0, required=True))
                        stop_reason = "budget_time"
                        break
                    if mem_cost and not self.safeguards.check_memory_cost(session_id, mem_cost):
                        if not DEBUG_MINIMAL_MENU_LOOP:
                            logger.warning("🛑 [LLM_ADAPTER] Budget coût mémoire atteint, arrêt de la boucle et RESPOND.")
                        chosen_actions.append(Action(ActionType.RESPOND, {}, priority=0, required=True))
                        stop_reason = "budget_memory_cost"
                        break
                    self.safeguards.record_reflection_usage(session_id, tokens=0, time_elapsed=0.0, memory_cost=mem_cost)
                    if not DEBUG_MINIMAL_MENU_LOOP:
                        try:
                            status = self.safeguards.get_budget_status(session_id)
                            logger.info(
                                "🛡️  [LLM_ADAPTER] Safeguards budget status (after action): "
                                f"tokens_remaining={status.get('tokens_remaining')}, "
                                f"time_remaining={status.get('time_remaining')}, "
                                f"memory_cost_remaining={status.get('memory_cost_remaining')}"
                            )
                        except Exception:
                            pass

            if stop_reason == "unknown":
                stop_reason = "max_iterations_reached"

            # Ensure RESPOND at end for traceability
            if not chosen_actions or chosen_actions[-1].type != ActionType.RESPOND:
                chosen_actions.append(Action(ActionType.RESPOND, {}, priority=0, required=True))

            # Normalize priorities in the resulting plan
            normalized_actions: List[Action] = []
            pr = 1
            for a in chosen_actions:
                normalized_actions.append(Action(a.type, dict(a.parameters or {}), priority=pr, required=a.required))
                pr += 1

            plan = ActionPlan(actions=normalized_actions, estimated_cost=0.0, confidence=0.5)
            planning_time = time.time() - planning_start

            # ExecutionResult must contain collected results (RESPOND has no result)
            execution_result = ExecutionResult(results=execution_results, success=True, errors=[], execution_time=0.0)
            execution_time = 0.0
            actions_seq = " -> ".join([a.type.value for a in plan.sorted_actions()])
            logger.info(
                f"✅ [LLM_ADAPTER] Boucle cognitive terminée: {len(plan.actions)} actions (dont RESPOND), "
                f"raison={stop_reason}, sequence={actions_seq}"
            )
            if self.safeguards and not DEBUG_MINIMAL_MENU_LOOP:
                try:
                    status = self.safeguards.get_budget_status(session_id)
                    logger.info(
                        "🛡️  [LLM_ADAPTER] Safeguards budget status (end): "
                        f"tokens_remaining={status.get('tokens_remaining')}, "
                        f"time_remaining={status.get('time_remaining')}, "
                        f"memory_cost_remaining={status.get('memory_cost_remaining')}"
                    )
                except Exception:
                    pass
            
            # 3. Générer la réponse finale directement à partir de la requête de base
            #    (dans l'esprit de `exemple_process.md` : après avoir choisi "Répondre", on répond).
            logger.info(f"🤖 [LLM_ADAPTER] Étape 3/5: Génération de la réponse finale...")
            generation_start = time.time()
            
            # Construire un résumé canonique de la séquence d'actions internes,
            # en format texte simple.
            # Dédupliquer pour éviter les répétitions dans le prompt final
            history_lines: List[str] = []
            seen_actions_final = set()
            for past_action in chosen_actions:
                # Éviter les répétitions de la même action
                action_key = past_action.type.value
                if action_key in seen_actions_final and past_action.type != ActionType.RESPOND:
                    continue  # Sauter les actions déjà vues (sauf RESPOND qui doit toujours apparaître)
                seen_actions_final.add(action_key)
                
                desc_choice = None
                if past_action.type in (
                    ActionType.CONSULT_MEMORY,
                    ActionType.CONSULT_INTERACTIONS,
                    ActionType.CONSULT_MEMORIES,
                ):
                    desc_choice = "choisir de consulter ta mémoire."
                elif past_action.type == ActionType.CONSULT_IDENTITY:
                    desc_choice = "choisir de connaitre ton identité."
                elif past_action.type == ActionType.CONSULT_TRAITS:
                    desc_choice = "choisir de connaitre tes traits."
                elif past_action.type == ActionType.CONSULT_ENVIRONMENT:
                    desc_choice = "choisir de connaitre ton environnement / capacités."
                elif past_action.type == ActionType.SEARCH_MEMORY:
                    desc_choice = "choisir d'explorer ta mémoire."
                elif past_action.type == ActionType.QUERY_EXTERNAL:
                    desc_choice = "choisir de consulter une source externe."
                elif past_action.type == ActionType.RESPOND:
                    desc_choice = "choisir de répondre directement à la demande de l'utilisateur."

                if desc_choice:
                    history_lines.append(
                        f"Pour traiter la demande de l'utilisateur, tu as décidé de {desc_choice}"
                    )

            history_block = "\n".join(history_lines)

            # Prompt final au format canonique (sections), sans imposer de style :
            # LIA voit l'historique, la demande, et un espace de sortie.
            final_prompt_parts: List[str] = []
            final_prompt_parts.append("=== HISTORIQUE INTERNE ===")
            if history_block:
                final_prompt_parts.append(history_block)
            else:
                final_prompt_parts.append("Aucune action interne n'a encore été enregistrée.")
            final_prompt_parts.append("")
            
            # Section: résultats des actions consultées (pour que LIA puisse les utiliser dans sa réponse)
            context_parts: List[str] = []
            if execution_results:
                # Extraction structurée pour les cas connus
                if execution_results.get(ActionType.CONSULT_IDENTITY.value):
                    identity_data = execution_results[ActionType.CONSULT_IDENTITY.value]
                    identity = identity_data.get("identity")
                    if identity:
                        context_parts.append(f"Identité: {identity}")
                if execution_results.get(ActionType.CONSULT_TRAITS.value):
                    traits_data = execution_results[ActionType.CONSULT_TRAITS.value]
                    traits = traits_data.get("traits", [])
                    if traits:
                        # Filtrer l'identité de base pour éviter la duplication
                        other_traits = [t for t in traits if t.get("label") != "Identité de Base"]
                        if other_traits:
                            context_parts.append("Traits:")
                            for trait in other_traits[:10]:  # Limiter à 10 traits
                                label = trait.get("label", "")
                                value = trait.get("value", "")
                                if label and value:
                                    context_parts.append(f"- {label}: {value}")
                if execution_results.get(ActionType.CONSULT_ENVIRONMENT.value):
                    env_data = execution_results[ActionType.CONSULT_ENVIRONMENT.value]
                    capabilities = env_data.get("capabilities", [])
                    if capabilities:
                        context_parts.append("Capacités:")
                        for cap in capabilities:
                            context_parts.append(f"- {cap}")
                if execution_results.get(ActionType.CONSULT_MEMORY.value):
                    memory_data = execution_results[ActionType.CONSULT_MEMORY.value]
                    memories = memory_data.get("memories", [])
                    if memories:
                        context_parts.append("Mémoires récentes:")
                        for mem in memories[:3]:  # Limiter à 3 mémoires
                            content = mem.get("content", "")
                            if content:
                                context_parts.append(f"- {content[:150]}...")

                # Fallback générique: si d'autres résultats sont présents, les exposer de façon compacte.
                # Cela garantit que même si la structure change (ou si une action n'est pas explicitement gérée),
                # le modèle voit quand même quelque chose.
                import json as _json  # éviter conflit avec json déjà importé plus haut
                known_keys = {
                    ActionType.CONSULT_IDENTITY.value,
                    ActionType.CONSULT_TRAITS.value,
                    ActionType.CONSULT_ENVIRONMENT.value,
                    ActionType.CONSULT_MEMORY.value,
                    ActionType.NAVIGATE_GENERAL.value,
                    ActionType.NAVIGATE_BASE.value,
                    "_menu_state",
                }
                for k, v in execution_results.items():
                    if k in known_keys:
                        continue
                    try:
                        text = v
                        if isinstance(v, (dict, list)):
                            text = _json.dumps(v, ensure_ascii=False)
                        text = str(text)
                        if not text:
                            continue
                        if len(text) > 200:
                            text = text[:200] + "..."
                        context_parts.append(f"Résultat {k}: {text}")
                    except Exception:
                        continue
            
            if context_parts:
                final_prompt_parts.append("=== INFORMATIONS CONSULTÉES ===")
                final_prompt_parts.append("\n".join(context_parts))
                final_prompt_parts.append("")
            
            final_prompt_parts.append("=== DEMANDE UTILISATEUR ===")
            final_prompt_parts.append(f'"{message}"')
            final_prompt_parts.append("")
            # Section de règle/style par défaut, au format canonique.
            # Formulée comme une description interne, pour éviter que LIA ne la répète.
            final_prompt_parts.append("=== STYLE ===")
            final_prompt_parts.append(
                "Cette section décrit ton style général et n'est pas une réponse à l'utilisateur."
            )
            final_prompt_parts.append(
                "Ton style par défaut est de répondre à la demande de l'utilisateur en langage naturel, de manière claire et compréhensible."
            )
            final_prompt_parts.append("")
            # Format canonique (définitions), sans imposer le contenu.
            final_prompt_parts.append("=== FORMAT ===")
            final_prompt_parts.append("HISTORIQUE INTERNE : résumé de tes actions internes (contexte).")
            final_prompt_parts.append("DEMANDE UTILISATEUR : la question / demande à traiter.")
            final_prompt_parts.append("STYLE : ton style général (contexte).")
            final_prompt_parts.append("SORTIE LIA : ce que tu envoies à l'utilisateur.")
            final_prompt_parts.append("")

            final_prompt_parts.append("=== SORTIE LIA ===")
            final_prompt_parts.append("")  # laisser une ligne vide pour la génération

            final_prompt = "\n".join(final_prompt_parts)
            logger.info(
                f"📝 [LLM_ADAPTER] Prompt final pour génération de la réponse:\n{final_prompt}"
            )

            use_gguf = (self.tokenizer is None)
            if use_gguf:
                response = self._generate_gguf(final_prompt)
                response = self._clean_response(response)
            else:
                import torch
                if not self.tokenizer:
                    raise RuntimeError("Tokenizer non chargé")

                encoded = self.tokenizer(
                    final_prompt,
                    return_tensors="pt",
                    padding=False,
                    truncation=True,
                    max_length=self.config.max_prompt_length,
                )
                input_ids = encoded["input_ids"].to(self.device)
                attention_mask = encoded.get("attention_mask", None)
                if attention_mask is not None:
                    attention_mask = attention_mask.to(self.device)

                with torch.no_grad():
                    generate_kwargs = {
                        "max_length": input_ids.shape[1] + self.config.max_length,
                        "num_return_sequences": 1,
                        "temperature": self.config.temperature,
                        "top_p": self.config.top_p,
                        "top_k": self.config.top_k,
                        "do_sample": True,
                        "pad_token_id": self.tokenizer.pad_token_id,
                        "eos_token_id": self.tokenizer.eos_token_id,
                        "repetition_penalty": self.config.repetition_penalty,
                    }
                    if attention_mask is not None:
                        generate_kwargs["attention_mask"] = attention_mask

                    outputs = self.model.generate(input_ids, **generate_kwargs)

                generated_ids = outputs[0][input_ids.shape[1] :]
                response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
                response = self._clean_response(response)

            # Ajouter le chunk de réponse finale à la trace
            final_chunk = ResponseChunk(
                type=ResponseChunkType.RESPONSE,
                content=response,
                metadata={
                    "session_id": session_id,
                    "stop_reason": stop_reason,
                    "actions_sequence": actions_seq,
                },
            )
            trace_chunks.append(final_chunk)
            # Pas de callback ici: c'est typiquement envoyé via le canal de réponse final
            generation_time = time.time() - generation_start
            logger.info(
                f"✅ [LLM_ADAPTER] Réponse générée: {len(response)} caractères, temps: {generation_time:.3f}s"
            )
            
            # En mode minimal, on s'arrête ici pour SelfVerifier / PatternLearner / métriques,
            # mais l'apprentissage simple de patterns de menus via Gemini peut rester actif.
            if not DEBUG_MINIMAL_MENU_LOOP:
                # 4. Vérifier la réponse
                logger.info("🔍 [LLM_ADAPTER] Étape 4/5: Vérification de la réponse...")
                verification_result = None
                if self.self_verifier:
                    verification_result = await self.self_verifier.verify(
                        user_message=message,
                        response=response,
                        execution_result=execution_result,
                        session_id=session_id
                    )
                    
                    logger.info(
                        f"🔍 Vérification: valid={verification_result.is_valid}, "
                        f"pertinence={verification_result.relevance_score:.2f}, "
                        f"mémoire={verification_result.memory_usage_score:.2f}, "
                        f"identité={verification_result.identity_coherence_score:.2f}, "
                        f"global={verification_result.overall_score:.2f}"
                    )
                    
                    if not verification_result.is_valid:
                        logger.warning(f"⚠️  Validation échouée: {verification_result.issues}")
                        # Pour l'instant, on accepte quand même (à améliorer avec re-planification)
                
                # 5. Enregistrer l'exécution pour apprentissage (Phase 3)
                logger.info(f"📚 [LLM_ADAPTER] Étape 5/5: Enregistrement pour apprentissage...")
                if self.pattern_learner:
                    try:
                        # Analyser la requête pour obtenir le type
                        request_analysis = self.cognitive_planner._analyze_request(message)
                        
                        self.pattern_learner.record_execution(
                            plan=plan,
                            execution_result=execution_result,
                            verification_result=verification_result,
                            request_analysis=request_analysis,
                            user_feedback=None  # À implémenter plus tard
                        )
                        logger.info("✅ [LLM_ADAPTER] Exécution enregistrée pour apprentissage (PatternLearner)")
                    except Exception as e:
                        logger.warning(f"⚠️  [LLM_ADAPTER] Erreur lors de l'enregistrement de l'exécution (PatternLearner): {e}")

                # 8. Décider quoi mémoriser de manière sélective (Phase 4)
                if self.memory_manager and self.memory:
                    try:
                        interaction = {
                            "prompt": message,
                            "response": response,
                            "session_id": session_id,
                        }
                        
                        # Décider quoi mémoriser
                        memory_items = await self.memory_manager.decide_what_to_store(
                            interaction=interaction,
                            execution_result=execution_result,
                            verification_result=verification_result
                        )
                        
                        # Stocker les éléments sélectionnés
                        if memory_items:
                            memory_ids = await self.memory_manager.store_memories(
                                items=memory_items,
                                session_id=session_id
                            )
                            logger.info(f"✅ [LLM_ADAPTER] {len(memory_ids)} souvenir(s) stocké(s) sélectivement")
                        else:
                            logger.debug("  ℹ️  [LLM_ADAPTER] Aucun élément à mémoriser (importance insuffisante)")
                    except Exception as e:
                        logger.warning(f"⚠️  [LLM_ADAPTER] Erreur lors de la gestion sélective de la mémoire: {e}")

            # 6. Journaliser l'interaction (toujours journaliser pour historique),
            # y compris en mode minimal : la mémorisation par phrases (MemoryRank V2)
            # doit rester active.
            if self.memory:
                try:
                    self.memory.log_interaction(
                        session_id=session_id,
                        prompt=message,
                        response=response,
                        severity="info"
                    )
                    logger.debug("✅ [LLM_ADAPTER] Interaction journalisée")
                    
                    # Traiter avec PhraseMemoryProcessor si activé (MemoryRank V2)
                    if self.phrase_processor:
                        try:
                            interaction = {
                                "prompt": message,
                                "response": response,
                                "session_id": session_id
                            }
                            stored_ids = await self.phrase_processor.process_interaction(interaction)
                            if stored_ids:
                                # Récupérer le contenu des phrases stockées pour les logs
                                stored_phrases_content = []
                                try:
                                    if self.phrase_processor and self.phrase_processor.store:
                                        from memory_service.models import SouvenirModel
                                        session = self.phrase_processor.store.db.get_session()
                                        try:
                                            memories = session.query(SouvenirModel).filter(
                                                SouvenirModel.memory_id.in_(stored_ids)
                                            ).all()
                                            stored_phrases_content = [
                                                {"id": m.memory_id[:8], "content": m.content, "importance": m.importance_score}
                                                for m in memories
                                            ]
                                        finally:
                                            session.close()
                                except Exception as e:
                                    logger.debug(f"Erreur récupération contenu phrases: {e}")
                                
                                logger.info(f"✅ [MEMORYRANK] {len(stored_ids)} phrases stockées via MemoryRank V2:")
                                for idx, phrase_info in enumerate(stored_phrases_content, 1):
                                    content_preview = phrase_info["content"][:100] + "..." if len(phrase_info["content"]) > 100 else phrase_info["content"]
                                    logger.info(f"  {idx}. [{phrase_info['id']}...] (I={phrase_info['importance']:.3f}): {content_preview}")
                            else:
                                logger.debug(f"ℹ️  [MEMORYRANK] Aucune phrase stockée (filtrage sémantique)")
                        except Exception as e:
                            logger.warning(f"⚠️  [MEMORYRANK] Erreur traitement par phrases: {e}")
                except Exception as e:
                    logger.warning(f"⚠️  [LLM_ADAPTER] Erreur lors de la journalisation: {e}")

            # Stocker les infos nécessaires pour apprentissage patterns différé (via app_chat.py)
            try:
                self._last_patterns_plan = plan
                self._last_patterns_request = message
                logger.info("🧠 [PATTERNS] Contexte patterns mémorisé pour apprentissage différé.")
            except Exception as e:
                logger.warning(f"⚠️  [LLM_ADAPTER] Impossible de mémoriser le contexte patterns: {e}")
                
                # 9. Enregistrer les métriques (Phase 5)
                if self.metrics:
                    try:
                        total_time = time.time() - start_time
                        cache_hits = 1 if (self.optimizer and self.optimizer.get_cached_plan(message, self.cognitive_planner._analyze_request(message))) else 0
                        cache_misses = 1 - cache_hits
                        
                        # Compter les accès mémoire (en important ActionType si disponible)
                        memory_accesses = 0
                        try:
                            from .cognitive_models import ActionType
                            memory_accesses = len([a for a in plan.actions if a.type in (ActionType.CONSULT_MEMORY, ActionType.CONSULT_MEMORIES, ActionType.CONSULT_INTERACTIONS)])
                        except ImportError:
                            # Si ActionType n'est pas disponible, compter toutes les actions sauf RESPOND
                            memory_accesses = len([a for a in plan.actions if a.type.value != "respond"])
                        
                        self.metrics.record_execution(
                            session_id=session_id,
                            planning_time=planning_time,
                            execution_time=execution_time,
                            total_time=total_time,
                            tokens_used=0,  # À calculer si disponible
                            actions_count=len(plan.actions),
                            memory_accesses=memory_accesses,
                            cache_hits=cache_hits,
                            cache_misses=cache_misses,
                            plan_confidence=plan.confidence,
                            verification_score=verification_result.overall_score if verification_result else 0.0,
                            success=execution_result.success,
                            errors=execution_result.errors if execution_result else []
                        )
                        logger.info(f"📊 [LLM_ADAPTER] Métriques enregistrées: total={total_time:.3f}s (plan={planning_time:.3f}s, exec={execution_time:.3f}s, gen={generation_time:.3f}s)")
                    except Exception as e:
                        logger.warning(f"⚠️  [LLM_ADAPTER] Erreur lors de l'enregistrement des métriques: {e}")
            
            logger.info(f"✅ [LLM_ADAPTER] Génération terminée avec succès (session: {session_id})")
            
            # En mode standard: retourner uniquement la réponse (comportement existant)
            # Les interfaces qui veulent la trace complète pourront utiliser une API dédiée.
            self._last_trace_chunks = trace_chunks  # stocker pour récupération optionnelle
            return response
            
        except Exception as e:
            error_msg = f"❌ ERREUR CRITIQUE dans le planificateur cognitif: {e}"
            logger.error(error_msg, exc_info=True)
            # PAS DE FALLBACK - lever l'exception pour voir les erreurs
            raise RuntimeError(error_msg) from e
    
    async def _generate_internal(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        use_classic_prompt: bool = True,
    ) -> str:
        """
        Génère une réponse avec le modèle LLM (méthode interne, sans autonomie).
        
        Args:
            message: Message de l'utilisateur
            context: Contexte mémoire (optionnel, sera récupéré depuis mémoire si None et mémoire activée)
            session_id: ID de session (optionnel, généré si None)
            use_classic_prompt:
                - True (défaut): construire le prompt complet avec identité / environnement / historique.
                - False: utiliser un prompt simple de type conversationnel "Utilisateur: ...\\nLIA:".
        
        Returns:
            Réponse générée
        """
        if not self.model:
            raise RuntimeError("Modèle non chargé")
        
        # Vérifier si on utilise GGUF (le modèle GGUF n'a pas de tokenizer)
        use_gguf = (self.tokenizer is None)
        
        # Générer un session_id si non fourni
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Construire le prompt
        if use_classic_prompt:
            # Ancien comportement : extraction de contexte mémoire + prompt riche (IDENTITÉ, ENVIRONNEMENT, etc.)
            if context is None and self.memory:
                try:
                    # Utiliser MemoryActivator si disponible pour un contexte actif
                    if self.memory_activator:
                        context = self.memory_activator.get_active_context(
                            message=message,
                            session_id=session_id,
                            limit_traits=10,
                            limit_memories=10,
                            limit_interactions=5
                        )
                        logger.info(f"📚 Contexte récupéré via MemoryActivator: {len(context.get('recent_interactions', []))} interactions")
                    else:
                        # Fallback vers récupération standard
                        context = self.memory.get_context(limit_interactions=5)
                        logger.info(f"📚 Contexte récupéré via MemoryAdapter: {len(context.get('recent_interactions', []))} interactions")
                    
                    # FORCER la présence de la mémoire dans le prompt
                    # Si pas de souvenirs, créer un contexte minimal mais présent
                    if not context.get("memories") or len(context.get("memories", [])) == 0:
                        try:
                            self.memory.add_memory_from_interaction(
                                content=f"Session en cours: {message[:100]}",
                                category="session",
                                importance_score=0.3
                            )
                            # Re-récupérer le contexte
                            if self.memory_activator:
                                context = self.memory_activator.get_active_context(
                                    message=message,
                                    session_id=session_id,
                                    limit_traits=10,
                                    limit_memories=10,
                                    limit_interactions=5
                                )
                            else:
                                context = self.memory.get_context(limit_interactions=5)
                            logger.debug("Souvenir de session créé pour activer la mémoire")
                        except Exception as e:
                            logger.debug(f"Impossible de créer un souvenir de session: {e}")
                    
                    logger.info(
                        f"📋 Contexte récupéré depuis mémoire: {len(context.get('traits', []))} traits, "
                        f"{len(context.get('memories', []))} souvenirs, {len(context.get('recent_interactions', []))} interactions"
                    )
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération du contexte: {e}")
                    context = {}
            
            prompt = self.build_prompt(message, context)
        else:
            # Nouveau comportement (intégré au système de menus) :
            # Prompt simple, style conversationnel, sans sections === IDENTITÉ ===.
            prompt = f"Utilisateur: {message}\nLIA:"
            logger.info(
                "📝 [LLM_ADAPTER] Prompt simple utilisé pour génération (sans sections IDENTITÉ/ENVIRONNEMENT)."
            )
        
        try:
            if use_gguf:
                # Génération avec GGUF (llama-cpp-python)
                response = self._generate_gguf(prompt)
                # Nettoyer la réponse
                response = self._clean_response(response)
            else:
                # Génération avec transformers
                if not self.tokenizer:
                    raise RuntimeError("Tokenizer non chargé")
                
                import torch
                
                # Encoder le prompt avec attention_mask
                encoded = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    padding=False,
                    truncation=True,
                    max_length=self.config.max_prompt_length
                )
                input_ids = encoded["input_ids"].to(self.device)
                attention_mask = encoded.get("attention_mask", None)
                if attention_mask is not None:
                    attention_mask = attention_mask.to(self.device)
                
                # Générer la réponse
                with torch.no_grad():
                    generate_kwargs = {
                        "max_length": input_ids.shape[1] + self.config.max_length,
                        "num_return_sequences": 1,
                        "temperature": self.config.temperature,
                        "top_p": self.config.top_p,
                        "top_k": self.config.top_k,
                        "do_sample": True,
                        "pad_token_id": self.tokenizer.pad_token_id,
                        "eos_token_id": self.tokenizer.eos_token_id,
                        "repetition_penalty": self.config.repetition_penalty
                    }
                    
                    # Ajouter attention_mask si disponible
                    if attention_mask is not None:
                        generate_kwargs["attention_mask"] = attention_mask
                    
                    outputs = self.model.generate(input_ids, **generate_kwargs)
                
                # Décoder la réponse
                # Pour Qwen avec chat template, extraire seulement les nouveaux tokens générés
                generated_ids = outputs[0][input_ids.shape[1]:]  # Prendre seulement les nouveaux tokens
                response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
                
                # Nettoyer la réponse
                response = self._clean_response(response)
            
            # Journaliser l'interaction dans la mémoire si disponible
            if self.memory:
                try:
                    self.memory.log_interaction(
                        session_id=session_id,
                        prompt=message,
                        response=response,
                        severity="info"
                    )
                    logger.debug("Interaction journalisée dans la mémoire")
                    
                    # Traiter avec PhraseMemoryProcessor si activé (MemoryRank V2)
                    if self.phrase_processor:
                        try:
                            interaction = {
                                "prompt": message,
                                "response": response,
                                "session_id": session_id
                            }
                            stored_ids = await self.phrase_processor.process_interaction(interaction)
                            if stored_ids:
                                # Récupérer le contenu des phrases stockées pour les logs
                                stored_phrases_content = []
                                try:
                                    if self.phrase_processor and self.phrase_processor.store:
                                        from memory_service.models import SouvenirModel
                                        session = self.phrase_processor.store.db.get_session()
                                        try:
                                            memories = session.query(SouvenirModel).filter(
                                                SouvenirModel.memory_id.in_(stored_ids)
                                            ).all()
                                            stored_phrases_content = [
                                                {"id": m.memory_id[:8], "content": m.content, "importance": m.importance_score}
                                                for m in memories
                                            ]
                                        finally:
                                            session.close()
                                except Exception as e:
                                    logger.debug(f"Erreur récupération contenu phrases: {e}")
                                
                                logger.info(f"✅ [MEMORYRANK] {len(stored_ids)} phrases stockées via MemoryRank V2:")
                                for idx, phrase_info in enumerate(stored_phrases_content, 1):
                                    content_preview = phrase_info["content"][:100] + "..." if len(phrase_info["content"]) > 100 else phrase_info["content"]
                                    logger.info(f"  {idx}. [{phrase_info['id']}...] (I={phrase_info['importance']:.3f}): {content_preview}")
                            else:
                                logger.debug(f"ℹ️  [MEMORYRANK] Aucune phrase stockée (filtrage sémantique)")
                        except Exception as e:
                            logger.warning(f"⚠️  [MEMORYRANK] Erreur traitement par phrases: {e}")
                except Exception as e:
                    logger.warning(f"Erreur lors de la journalisation: {e}")
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur génération: {e}", exc_info=True)
            raise Exception(f"Erreur génération: {e}")
    
    async def _generate_gguf_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AsyncIterator[str]:
        """Génère une réponse avec streaming pour modèle GGUF."""
        # Tronquer le prompt si nécessaire (même logique que _generate_gguf)
        max_chars_for_prompt = (self.config.max_prompt_length - self.config.max_length) * 4
        if len(prompt) > max_chars_for_prompt:
            # Utiliser la même logique de troncature que _generate_gguf
            lines = prompt.split("\n")
            identity_start = 0
            interactions_start = -1
            current_question_start = -1
            
            for i, line in enumerate(lines):
                if "=== IDENTITÉ" in line or "Je me nomme LIA" in line:
                    identity_start = i
                if "Utilisateur:" in line and interactions_start == -1:
                    interactions_start = i
                if ("=== Conversation Actuelle ===" in line or 
                    "=== CONVERSATION ACTUELLE ===" in line or
                    ("Utilisateur:" in line and i > len(lines) - 5)):
                    current_question_start = i
                    break
            
            if current_question_start > 0:
                identity_section = "\n".join(lines[identity_start:min(identity_start+20, interactions_start if interactions_start > 0 else len(lines))])
                interactions_section = "\n".join(lines[interactions_start:current_question_start]) if interactions_start > 0 else ""
                current_section = "\n".join(lines[current_question_start:])
                
                current_len = len(current_section)
                identity_len = len(identity_section)
                available = max_chars_for_prompt - current_len - identity_len - 100
                
                if available > 0 and interactions_section:
                    if len(interactions_section) > available:
                        interactions_lines = interactions_section.split("\n")
                        kept_lines = []
                        current_size = 0
                        for line in reversed(interactions_lines):
                            if current_size + len(line) < available:
                                kept_lines.insert(0, line)
                                current_size += len(line)
                            else:
                                break
                        interactions_section = "\n".join(kept_lines)
                    prompt = f"{identity_section}\n\n{interactions_section}\n\n{current_section}"
                else:
                    prompt = f"{identity_section}\n\n{current_section}"
            else:
                prompt = prompt[-max_chars_for_prompt:]
        
        # Générer avec llama-cpp-python en streaming
        # Note: llama-cpp-python ne supporte pas directement le streaming async
        # On va simuler le streaming en générant par petits batches
        stop_sequences = [
            "\n\n\n",
            "\n\nUtilisateur:",
            "\nUtilisateur :",
            "Utilisateur :",
            "=== Conversation ===",
            "### Définition",
            "### Fonctionnement",
            "### Types",
            "[Échange précédent",
            "Voici les réponses",
            "Réponse :",
            "Question :",
        ]
        
        # Pour GGUF, on génère token par token
        # On utilise une approche de génération progressive
        generated_text = ""
        max_tokens = self.config.max_length
        
        # Générer par petits chunks pour simuler le streaming
        for i in range(max_tokens):
            # Générer un token à la fois
            output = self.model(
                prompt + generated_text,
                max_tokens=1,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repeat_penalty=self.config.repetition_penalty,
                stop=stop_sequences,
                echo=False
            )
            
            if isinstance(output, dict) and "choices" in output:
                new_text = output["choices"][0].get("text", "")
            elif isinstance(output, dict) and "text" in output:
                new_text = output["text"]
            else:
                new_text = str(output)
            
            if not new_text:
                break
            
            # Vérifier les stop sequences
            should_stop = False
            for stop_seq in stop_sequences:
                if stop_seq in new_text:
                    should_stop = True
                    # Extraire seulement la partie avant le stop
                    stop_idx = new_text.find(stop_seq)
                    if stop_idx >= 0:
                        new_text = new_text[:stop_idx]
                    break
            
            if new_text:
                generated_text += new_text
                yield new_text
                
                # Appeler le callback si fourni
                if stream_callback:
                    try:
                        await stream_callback(new_text)
                    except Exception as cb_err:
                        logger.debug(f"Erreur callback streaming: {cb_err}")
            
            if should_stop:
                break
    
    async def _generate_transformers_stream(
        self,
        prompt: str,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AsyncIterator[str]:
        """Génère une réponse avec streaming pour modèle transformers."""
        import torch
        
        if not self.tokenizer:
            raise RuntimeError("Tokenizer non chargé")
        
        # Encoder le prompt
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=False,
            truncation=True,
            max_length=self.config.max_prompt_length
        )
        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded.get("attention_mask", None)
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)
        
        # Générer avec streaming
        with torch.no_grad():
            # Utiliser generate avec streamer si disponible (transformers >= 4.35)
            # Sinon, générer token par token
            try:
                from transformers import TextIteratorStreamer
                import threading
                import queue
                
                streamer = TextIteratorStreamer(
                    self.tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True
                )
                
                generation_kwargs = {
                    "input_ids": input_ids,
                    "max_length": input_ids.shape[1] + self.config.max_length,
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "top_k": self.config.top_k,
                    "do_sample": True,
                    "pad_token_id": self.tokenizer.pad_token_id,
                    "eos_token_id": self.tokenizer.eos_token_id,
                    "repetition_penalty": self.config.repetition_penalty,
                    "streamer": streamer
                }
                
                if attention_mask is not None:
                    generation_kwargs["attention_mask"] = attention_mask
                
                # Lancer la génération dans un thread séparé
                generation_thread = threading.Thread(
                    target=self.model.generate,
                    kwargs=generation_kwargs
                )
                generation_thread.start()
                
                # Lire les tokens depuis le streamer
                for token in streamer:
                    if token:
                        yield token
                        if stream_callback:
                            try:
                                await stream_callback(token)
                            except Exception as cb_err:
                                logger.debug(f"Erreur callback streaming: {cb_err}")
                
                generation_thread.join()
                
            except ImportError:
                # Fallback: génération token par token
                logger.warning("TextIteratorStreamer non disponible, utilisation du fallback token par token")
                
                current_ids = input_ids
                generated_text = ""
                
                for _ in range(self.config.max_length):
                    with torch.no_grad():
                        outputs = self.model.generate(
                            current_ids,
                            max_length=current_ids.shape[1] + 1,
                            num_return_sequences=1,
                            temperature=self.config.temperature,
                            top_p=self.config.top_p,
                            top_k=self.config.top_k,
                            do_sample=True,
                            pad_token_id=self.tokenizer.pad_token_id,
                            eos_token_id=self.tokenizer.eos_token_id,
                            repetition_penalty=self.config.repetition_penalty
                        )
                    
                    # Extraire le nouveau token
                    new_token_id = outputs[0][-1:]
                    new_token_text = self.tokenizer.decode(new_token_id, skip_special_tokens=True)
                    
                    if new_token_text and new_token_text != self.tokenizer.eos_token:
                        generated_text += new_token_text
                        yield new_token_text
                        
                        if stream_callback:
                            try:
                                await stream_callback(new_token_text)
                            except Exception as cb_err:
                                logger.debug(f"Erreur callback streaming: {cb_err}")
                        
                        current_ids = torch.cat([current_ids, new_token_id], dim=1)
                    else:
                        break
    
    def _generate_gguf(self, prompt: str) -> str:
        """Génère une réponse avec un modèle GGUF (llama-cpp-python)."""
        # Log du prompt avant génération (pour debug)
        prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
        logger.info(f"🔍 Prompt envoyé au modèle GGUF (preview, {len(prompt)} caractères):\n{prompt_preview}")
        
        # Tronquer le prompt si trop long - PRÉSERVER LES INTERACTIONS
        # Avec n_ctx=32768 tokens, on a beaucoup d'espace
        # Limite pour le prompt = (max_prompt_length - max_length) * 4 caractères
        # Exemple: (32768 - 512) * 4 = 129024 caractères (~126 KB)
        max_chars_for_prompt = (self.config.max_prompt_length - self.config.max_length) * 4
        max_chars = max_chars_for_prompt
        original_length = len(prompt)
        estimated_tokens = len(prompt) // 4
        
        logger.info(f"📏 Taille prompt: {len(prompt)} caractères (~{estimated_tokens} tokens), limite: {max_chars} caractères (~{max_chars_for_prompt//4} tokens)")
        
        if len(prompt) > max_chars:
            # Stratégie intelligente : préserver l'identité, les interactions et la question actuelle
            # Chercher les sections importantes
            lines = prompt.split("\n")
            
            # Trouver les sections importantes
            identity_start = 0
            interactions_start = -1
            current_question_start = -1
            
            for i, line in enumerate(lines):
                if "=== IDENTITÉ" in line or "Je me nomme LIA" in line:
                    identity_start = i
                if "Utilisateur:" in line and interactions_start == -1:
                    # Première interaction trouvée
                    interactions_start = i
                if (
                    "=== Conversation Actuelle ===" in line
                    or "=== CONVERSATION ACTUELLE ===" in line
                    or ("Utilisateur:" in line and i > len(lines) - 5)
                ):
                    # Question actuelle (dans les 5 dernières lignes)
                    current_question_start = i
                    break
            
            # Construire le prompt tronqué en préservant les sections importantes
            if current_question_start > 0:
                # Garder : identité (début) + interactions (milieu) + question actuelle (fin)
                identity_section = "\n".join(lines[identity_start:min(identity_start+20, interactions_start if interactions_start > 0 else len(lines))])
                interactions_section = "\n".join(lines[interactions_start:current_question_start]) if interactions_start > 0 else ""
                current_section = "\n".join(lines[current_question_start:])
                
                # Calculer l'espace disponible
                current_len = len(current_section)
                identity_len = len(identity_section)
                available = max_chars - current_len - identity_len - 100  # 100 chars de marge
                
                if available > 0 and interactions_section:
                    # Tronquer les interactions si nécessaire, mais les garder
                    if len(interactions_section) > available:
                        # Garder la fin des interactions (plus récentes)
                        interactions_lines = interactions_section.split("\n")
                        kept_lines = []
                        current_size = 0
                        for line in reversed(interactions_lines):
                            if current_size + len(line) < available:
                                kept_lines.insert(0, line)
                                current_size += len(line)
                            else:
                                break
                        interactions_section = "\n".join(kept_lines)
                        logger.warning(f"⚠️  Interactions partiellement tronquées pour tenir dans la limite")
                    
                    prompt = f"{identity_section}\n\n{interactions_section}\n\n{current_section}"
                else:
                    # Si pas assez de place, garder au moins identité + question actuelle
                    prompt = f"{identity_section}\n\n{current_section}"
                    logger.warning(f"⚠️  Interactions supprimées pour tenir dans la limite (prompt trop long)")
            else:
                # Fallback : tronquer depuis le début mais garder la fin
                prompt = prompt[-max_chars:]
                logger.warning(f"⚠️  Prompt tronqué de {original_length} à {max_chars} caractères (troncature simple)")
            
            logger.warning(f"⚠️  Prompt tronqué de {original_length} à {len(prompt)} caractères")
            # Log après troncature
            prompt_preview_after = prompt[:500] + "..." if len(prompt) > 500 else prompt
            logger.info(f"🔍 Prompt après troncature (preview):\n{prompt_preview_after}")
        
        # Si disponible, utiliser le mode chat (system/user/assistant) pour réduire les fuites de prompt.
        if hasattr(self.model, "create_chat_completion"):
            system_content = ""
            user_content = prompt

            # Heuristique: si prompt au format canonique, extraire la demande utilisateur
            # et passer le reste en contexte système.
            try:
                if "=== DEMANDE UTILISATEUR ===" in prompt:
                    before, after = prompt.split("=== DEMANDE UTILISATEUR ===", 1)
                    system_content = before.strip()
                    # Extraire les lignes de la demande jusqu'à la prochaine section
                    user_lines: List[str] = []
                    for line in after.splitlines():
                        if line.strip().startswith("==="):
                            break
                        if line.strip():
                            user_lines.append(line.strip())
                    user_content = "\n".join(user_lines).strip() or prompt

                    # Enlever les sections "SORTIE" du système si elles apparaissent avant
                    if "=== SORTIE LIA ===" in system_content:
                        system_content = system_content.split("=== SORTIE LIA ===", 1)[0].strip()
            except Exception:
                system_content = ""
                user_content = prompt

            chat_messages = []
            if system_content:
                chat_messages.append({"role": "system", "content": system_content})
            chat_messages.append({"role": "user", "content": user_content})

            output = self.model.create_chat_completion(
                messages=chat_messages,
                max_tokens=self.config.max_length,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repeat_penalty=self.config.repetition_penalty,
                stop=[
                    "\n\n\n",
                    "=== HISTORIQUE",
                    "=== DEMANDE",
                    "=== STYLE",
                    "=== FORMAT",
                    "=== SORTIE",
                ],
            )

            # Extraire le texte généré (format chat)
            try:
                response = output["choices"][0]["message"]["content"]
            except Exception:
                # Fallback: certains wrappers peuvent renvoyer "text"
                response = output["choices"][0].get("text") if isinstance(output, dict) else str(output)
        else:
            # Génération en mode completion (fallback)
            output = self.model(
                prompt,
                max_tokens=self.config.max_length,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repeat_penalty=self.config.repetition_penalty,
                stop=[
                    "\n\n\n",  # Triple saut de ligne
                    "\n\nUtilisateur:",  # Nouvelle question utilisateur
                    "\nUtilisateur :",  # Variante avec espace
                    "Utilisateur :",  # Variante au début de ligne
                    "=== Conversation ===",  # Nouvelle section
                    "### Définition",  # Section technique
                    "### Fonctionnement",  # Section technique
                    "### Types",  # Section technique
                    "[Échange précédent",  # Référence à un échange
                    "Voici les réponses",  # Début de liste
                    "Réponse :",  # Format de réponse technique
                    "Question :",  # Format de question technique
                ],
                echo=False  # Ne pas répéter le prompt
            )

            # Extraire le texte généré
            if isinstance(output, dict) and "choices" in output:
                response = output["choices"][0]["text"]
            elif isinstance(output, dict) and "text" in output:
                response = output["text"]
            else:
                # Fallback: convertir en string
                response = str(output)
        
        return response.strip()

    # ------------------------------------------------------------------
    # Système de patterns (menus) avec agent interne - helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Système de patterns (menus) avec Gemini - SYSTEME_PATTERNS.md
    # ------------------------------------------------------------------

    def _compute_order_weights(self, sequence: List[str]) -> Dict[str, float]:
        """Calcule les poids d'une séquence selon l'ordre.

        Formule (doc SYSTEME_PATTERNS) :
            poids(action_i) = (n - i + 1) / somme(1..n), i commençant à 1.
        Si un même code apparaît plusieurs fois, on additionne ses contributions
        puis on renormalise pour que la somme totale vaille 1.0.
        """
        n = len(sequence)
        if n == 0:
            return {}
        denom = n * (n + 1) / 2.0  # somme(1..n)
        weights: Dict[str, float] = {}
        for idx, code in enumerate(sequence, start=1):
            contrib = (n - idx + 1) / denom
            weights[code] = weights.get(code, 0.0) + contrib

        total = sum(weights.values())
        if total > 0:
            for k in list(weights.keys()):
                weights[k] = weights[k] / total
        return weights

    def _build_menu_pattern_sequence(self, plan) -> List[str]:
        """Construit la séquence de codes (B1, B2, G1, ...) à partir du plan exécuté.

        On simule le changement de contexte de menu:
        - Contexte initial: "base"
        - NAVIGATE_GENERAL → bascule vers "general"
        - NAVIGATE_BASE → bascule vers "base"
        """
        try:
            from .cognitive_models import ActionType
        except ImportError:
            return []

        if not plan or not getattr(plan, "sorted_actions", None):
            return []

        ctx = "base"
        codes: List[str] = []

        for action in plan.sorted_actions():
            t = getattr(action, "type", None)
            if t is None:
                continue

            if ctx == "base":
                if t == ActionType.CONSULT_REQUEST:
                    codes.append("B1")
                elif t == ActionType.NAVIGATE_GENERAL:
                    codes.append("B2")
                    ctx = "general"
                elif t == ActionType.RESPOND:
                    codes.append("B3")
            else:  # ctx == "general"
                if t == ActionType.CONSULT_IDENTITY:
                    codes.append("G1")
                elif t == ActionType.CONSULT_TRAITS:
                    codes.append("G2")
                elif t == ActionType.CONSULT_ENVIRONMENT:
                    codes.append("G3")
                elif t == ActionType.CONSULT_MEMORY:
                    codes.append("G4")
                elif t == ActionType.RESPOND:
                    codes.append("G5")
                elif t == ActionType.NAVIGATE_BASE:
                    codes.append("G6")
                    ctx = "base"

        return codes

    def _build_theme_classification_prompt(self, user_request: str) -> str:
        """Construit le prompt pour la classification du thème (V2, Étape 1).
        
        Enrichi avec :
        - Liste des actions disponibles (pour contexte)
        - Exemples de patterns par thème (si disponibles)
        - Descriptions des thèmes
        """
        themes = []
        theme_examples = {}
        if self.memory and hasattr(self.memory, "list_theme_patterns"):
            try:
                themes = self.memory.list_theme_patterns()
                if hasattr(self.memory, "get_theme_examples"):
                    theme_examples = self.memory.get_theme_examples(limit_per_theme=2)
            except Exception:
                pass
        if not themes:
            # Si aucun thème n'existe encore en base, on démarre avec un ensemble minimal.
            # Les autres thèmes émergent progressivement via l'apprentissage (V2).
            themes = ["no_pattern"]
        themes_str = ", ".join(f'"{t}"' for t in themes)
        
        # Descriptions des thèmes (pour guider la classification)
        theme_descriptions = {
            
            "no_pattern": "Pattern par défaut (non classifié)"
        }
        
        # S'assurer que les thèmes par défaut sont inclus même s'ils n'existent pas encore
        default_themes = ["no_pattern"]
        for default_theme in default_themes:
            if default_theme not in themes:
                themes.append(default_theme)
        
        lines = [
            "Tu es un assistant de classification de requêtes.",
            f"Requête de l'utilisateur : \"{user_request}\"",
            "",
            "Contexte : Voici les actions disponibles dans le système :",
        ]
        
        # Ajouter la liste des actions avec codes
        for code, desc in PATTERN_ACTIONS_CATALOG.items():
            lines.append(f"  - {code} : {desc}")
        
        lines.append("")
        lines.append(f"Thèmes disponibles : {themes_str}")
        lines.append("")
        lines.append("Descriptions des thèmes :")
        for theme in themes:
            desc = theme_descriptions.get(theme, "Thème non décrit")
            lines.append(f"  - {theme} : {desc}")
        
        # Ajouter des exemples de patterns par thème si disponibles
        if theme_examples:
            lines.append("")
            lines.append("Exemples de patterns par thème (pour référence) :")
            for theme, patterns in theme_examples.items():
                if patterns:
                    examples_str = ", ".join([
                        f"{p['menu_context']}/{p['prev_step']}→{p['recommended_step']}"
                        for p in patterns[:2]
                    ])
                    lines.append(f"  - {theme} : {examples_str}")
        
        lines.append("")
        lines.append("Ta tâche : choisis UN SEUL thème auquel pourrait appartenir cette requête.")
        lines.append(
            "Si aucun thème existant ne convient vraiment, tu peux proposer un NOUVEAU nom de thème, "
            "court et descriptif (1 à 3 mots) qui résume au mieux la requête."
        )
        lines.append("Réponds UNIQUEMENT avec le nom du thème, sans autre texte.")
        
        return "\n".join(lines)

    async def _classify_request_theme(self, user_request: str) -> Optional[str]:
        """Classe la requête dans un thème via Groq/Gemini (V2, Étape 1)."""
        adapter = self.groq_adapter or self.gemini_adapter
        if not adapter:
            return None
        prompt = self._build_theme_classification_prompt(user_request)
        try:
            raw = await adapter.query(prompt)  # type: ignore[func-returns-value]
        except Exception as e:
            logger.debug(f"🔍 [PATTERNS] Classification thème échouée: {e}")
            return None
        raw = (raw or "").strip()
        if not raw:
            return None
        # Normaliser : prendre la première ligne, extraire un mot/thème
        first_line = raw.split("\n")[0].strip()
        # Supprimer guillemets éventuels
        theme = first_line.strip('"\'')
        if theme and len(theme) < 80:
            # Créer le thème s'il n'existe pas encore (pour les thèmes par défaut comme "identité")
            if self.memory and hasattr(self.memory, "add_theme_pattern"):
                try:
                    existing = self.memory.list_theme_patterns()
                    if theme not in existing:
                        self.memory.add_theme_pattern(theme)
                        logger.debug(f"📚 [PATTERNS] Thème créé automatiquement lors de la classification: {theme}")
                except Exception:
                    pass
            return theme
        return None

    def _build_pattern_gemini_question(
        self,
        user_request: str,
        executed_sequence: List[str],
        use_v2_format: bool = True,
    ) -> str:
        """Construit le prompt envoyé à Gemini pour recommander une suite optimale.

        Prompt ORIGINAL conservé intégralement. En mode V2, on AJOUTE une section
        (thèmes + directives) et on adapte le format de sortie à {{theme_pattern},{B2, G3, G5}}.
        """
        lines: List[str] = []
        # --- PROMPT ORIGINAL (inchangé) ---
        lines.append("Tu es un assistant d'analyse de stratégies internes.")
        lines.append(
            "Tu analyses des suites d'actions internes (menus) choisies par un agent cognitif (LIA) "
            "pour traiter une requête utilisateur."
        )
        lines.append("")
        lines.append("CONTRAINTE IMPORTANTE :")
        lines.append(
            "- Ta sortie doit être UNIQUEMENT une suite de codes sous la forme : {Xy, Xy, Xy, ...}"
        )
        lines.append("- X est une lettre (B ou G), y est un entier (1, 2, 3, ...).")
        lines.append("- N'ajoute AUCUN autre texte avant ou après cette suite.")
        lines.append("")

        # Contraintes explicites de menus / transitions (même texte que scripts/test_patterns_gemini.py)
        lines.append("Contraintes de menus et de transitions (IMPORTANT) :")
        lines.append("- Tu démarres TOUJOURS dans le menu de base.")
        lines.append("- Dans le menu de base, tu ne peux utiliser que les codes B1, B2, B3.")
        lines.append("- Si tu choisis B2, tu passes au menu général.")
        lines.append("- Dans le menu général, tu ne peux utiliser que les codes G1, G2, G3, G4, G5, G6.")
        lines.append("- Dans le menu général, la SEULE façon de revenir au menu de base est de choisir G6,")
        lines.append("  puis tu peux de nouveau utiliser uniquement B1, B2, B3.")
        lines.append("- Tu ne dois JAMAIS proposer une transition impossible, par exemple :")
        lines.append("  - utiliser B3 immédiatement après G1 (sans passer par G6 pour revenir au menu de base),")
        lines.append("  - utiliser G1 immédiatement après B3 (car après B3, on ne revient pas dans le menu, le traitement de la requête est terminé).")
        lines.append("- Toutes les suites que tu proposes doivent donc être EXÉCUTABLES dans ce système de menus hierarchique.")
        lines.append("")

        lines.append("Contexte :")
        lines.append(f'- Requête de l\'utilisateur : "{user_request}"')
        lines.append("")
        lines.append("- Liste d'actions possibles (codes → description) :")
        for code, desc in PATTERN_ACTIONS_CATALOG.items():
            lines.append(f"  - {code} : {desc}")
        lines.append("")

        if executed_sequence:
            seq_str = ", ".join(executed_sequence)
            lines.append(
                f"- Suite d'actions réellement choisie par LIA pour cette requête : "
                f"{{{seq_str}}}"
            )
        else:
            lines.append("- Aucune action n'a encore été choisie par LIA (début de traitement).")
        lines.append("")

        lines.append("Ta tâche :")
        lines.append(
            "1. Proposer une suite de choix internes OPTIMALE pour traiter cette requête utilisateur."
        )
        lines.append(
            "2. Utiliser UNIQUEMENT des codes présents dans la liste d'actions ci-dessus."
        )
        lines.append(
            "3. Ne pas inventer de nouveaux codes ou de nouvelles actions."
        )

        # --- SECTION AJOUTÉE (V2) : thèmes + format {{nom_du_thème},{B2, G3, G5}} ---
        if use_v2_format:
            themes: List[str] = []
            if self.memory and hasattr(self.memory, "list_theme_patterns"):
                try:
                    themes = self.memory.list_theme_patterns()
                except Exception:
                    pass
            if not themes:
                themes = ["no_pattern"]
            themes_str = ", ".join(f'"{t}"' for t in themes)
            lines.append("")
            lines.append(
                f"En plus : Pour cette requête \"{user_request}\", voici les thèmes disponibles "
                f"dans la base : {themes_str}."
            )
            lines.append("Vous pouvez choisir UN pattern parmi cette liste pour classer la requête.")
            lines.append(
                "Soit si aucun pattern existant ne satisfait la demande, donner un NOUVEAU pattern "
                "(ex: greeting, ...) — il est important de savoir que du pattern auront un impact sur les traitements des futures requêtes avec la liste d'actions. Plus elle sont spécifique plus on aura de la précision dans les traitements de requettes."
            )
            lines.append(
                "Attention à la nuance, exemple: Classer les question \"Qui es-tu ?\" et \"Que connais-tu de moi ?\" dans le pattern \"identité\". C'est correct mais fausse car ce n'est pas la même identité qui est demandée. La première celle de LIA et la seconde celle de l'utilisateur."
            )
            lines.append("")
            lines.append("Format de réponse EXIGÉ : {{nom_du_thème},{B2, G4, G5}}")
            lines.append("Exemples valides : {{salutation},{B3}} ou {{mémoire},{B2, G4, G5}}")
        else:
            lines.append("")
            lines.append("Format de réponse EXIGÉ :")
            lines.append("- Une seule ligne de la forme : {B2, G4, G5}")

        lines.append("- Sans introduction, sans explication, sans texte additionnel.")
        lines.append("")
        lines.append("Réponds maintenant avec UNIQUEMENT la suite optimale au format demandé.")

        return "\n".join(lines)

    def _parse_pattern_sequence(self, raw: str, allowed_codes: List[str]) -> List[str]:
        """Parse la suite `{Xy, Xy, ...}` ou `{{theme},{Xy, Xy, ...}}` renvoyée par Gemini.

        Rétrocompatibilité : accepte les deux formats.
        Retourne uniquement la liste des codes (sans le thème).
        """
        _, seq = self._parse_pattern_response_v2(raw, allowed_codes)
        return seq

    def _parse_pattern_response_v2(
        self, raw: str, allowed_codes: List[str]
    ) -> tuple[Optional[str], List[str]]:
        """Parse la réponse Gemini V2 : {{theme},{B2, G3, G5}} → (theme, [B2, G3, G5]).

        Accepte aussi le format V1 : {B2, G3, G5} → (None, [B2, G3, G5]).
        """
        if not raw:
            return (None, [])

        raw = raw.strip()
        allowed_set = set(allowed_codes)
        theme: Optional[str] = None
        inside: str = raw

        # Format V2 : {{theme},{B2, G3, G5}}
        m_v2 = re.search(r"\{\{([^{}]*)\},\s*\{([^}]*)\}\}", raw)
        if m_v2:
            theme_raw = (m_v2.group(1) or "").strip()
            # Nettoyer les guillemets éventuels (simples ou doubles)
            theme_raw = theme_raw.strip('"\'')
            if theme_raw and len(theme_raw) < 80:
                theme = theme_raw
            inside = m_v2.group(2) or ""
        else:
            # Format V1 : {B2, G3, G5}
            m = re.search(r"\{([^}]*)\}", raw)
            inside = m.group(1) if m else raw

        candidates = re.findall(r"[A-Z]\d+", inside)
        seq = [c for c in candidates if c in allowed_set]
        return (theme, seq)

    def _filter_valid_pattern_sequence(self, sequence: List[str]) -> List[str]:
        """Valide/répare une séquence de codes pour qu'elle soit exécutable dans l'automate de menus.

        Règles:
        - Contexte initial: "base"
        - En "base": actions possibles = B1, B2, B3
            - B2 → passe au contexte "general"
        - En "general": actions possibles = G1..G6
            - G6 → revient au contexte "base"
        - Réparations:
            - Si on est en "general" et qu'on rencontre un code "B*":
                - si c'est "B3" (répondre), on le remplace par "G5" (répondre en menu général) et on termine.
                - sinon, on insère "G6" avant (retour base) puis on traite le code "B*".
        - Si une action de réponse est choisie (B3 ou G5), la suite se termine.
        """
        ctx = "base"
        valid: List[str] = []
        for code in sequence:
            code = (code or "").strip()
            if not code:
                continue

            if ctx == "base":
                # Cas normal: seules B1, B2, B3 sont possibles
                if code in ("B1", "B2", "B3"):
                    valid.append(code)
                    if code == "B2":
                        ctx = "general"
                    if code == "B3":
                        # Réponse en base → fin de séquence
                        break
                    continue

                # Nouveau comportement: si on voit un G* en base,
                # on insère automatiquement B2 pour entrer dans le menu général.
                if code.startswith("G"):
                    logger.info(
                        "ℹ️  [PATTERNS] Réparation de séquence: insertion de B2 avant %s pour passer du menu base au menu général.",
                        code,
                    )
                    # Insérer la transition vers le menu général
                    valid.append("B2")
                    ctx = "general"
                    # et on laisse le traitement se poursuivre plus bas en contexte général
                else:
                    # Code impossible en base (ni B*, ni G*) → on arrête.
                    break

            # ctx == "general"
            if code.startswith("B"):
                # réparation: B3 en general => G5, sinon insérer G6 puis traiter en base
                if code == "B3":
                    valid.append("G5")
                    break
                valid.append("G6")
                ctx = "base"
                # retraiter le code courant en base
                if code not in ("B1", "B2", "B3"):
                    break
                valid.append(code)
                if code == "B2":
                    ctx = "general"
                if code == "B3":
                    break
                continue

            if code not in ("G1", "G2", "G3", "G4", "G5", "G6"):
                break
            valid.append(code)
            if code == "G6":
                ctx = "base"
            if code == "G5":
                # Réponse en général → fin de séquence
                break

        return valid


    async def _learn_menu_patterns_with_agent(
        self,
        user_request: str,
        plan,
    ) -> None:
        """Apprend des patterns de menus via un modèle externe et met à jour la table `patterns`.

        Phase 1 (SYSTEME_PATTERNS.md) :
        - Collecter la suite d'actions exécutée
        - Envoyer la requête à Gemini (ou ignorer si indisponible)
        - Parser la réponse (format `{Xy, Xy, ...}`)
        - Calculer les poids selon l'ordre
        - Stocker dans la mémoire (table `patterns`)
        """
        # Important: sérialiser pour éviter des appels concurrents au modèle (GGUF) et à la DB.
        async with self._patterns_learning_lock:
            # Nécessite la mémoire + un adaptateur externe (Groq ou Gemini) disponible
            if not self.memory:
                logger.info("ℹ️  [PATTERNS] Mémoire indisponible, apprentissage patterns ignoré.")
                return
            adapter = self.groq_adapter or self.gemini_adapter
            if not adapter:
                logger.info("ℹ️  [PATTERNS] Aucun adaptateur externe disponible (Groq/Gemini), apprentissage patterns ignoré.")
                return

            executed_sequence = self._build_menu_pattern_sequence(plan)
            logger.info(f"🧠 [PATTERNS] Séquence d'actions exécutée (codes): {executed_sequence}")
            if not executed_sequence:
                logger.info("ℹ️  [PATTERNS] Séquence vide, rien à apprendre.")
                return

            question = self._build_pattern_gemini_question(
                user_request=user_request,
                executed_sequence=executed_sequence,
                use_v2_format=True,
            )
            # Log du prompt envoyé (tronqué pour rester lisible)
            preview_q = question if len(question) <= 800 else question[:800] + "..."
            logger.info(f"📝 [PATTERNS] Prompt envoyé à Gemini (apprentissage patterns):\n{preview_q}")

            # Appeler Gemini directement pour obtenir la suite optimale
            allowed_codes = list(PATTERN_ACTIONS_CATALOG.keys())

            raw = ""
            theme_pattern: Optional[str] = None
            parsed: List[str] = []
            try:
                raw = await adapter.query(question)  # type: ignore[func-returns-value]
            except Exception as e:
                err_msg = str(e).strip() or repr(e)
                logger.warning(
                    "⚠️  [PATTERNS] Appel Gemini pour apprentissage patterns échoué: %s - %s",
                    type(e).__name__,
                    err_msg,
                )
                return

            preview_a = raw if len(raw or "") <= 400 else (raw or "")[:400] + "..."
            adapter_name = "Groq" if self.groq_adapter else "Gemini"
            logger.info(f"📝 [PATTERNS] Réponse brute {adapter_name} (patterns):\n{preview_a}")

            # Parser la réponse V2 : {{theme},{B2, G3, G5}} ou V1 : {B2, G3, G5}
            theme_pattern, parsed = self._parse_pattern_response_v2(raw or "", allowed_codes)

            if not parsed:
                logger.warning(
                    "⚠️  [PATTERNS] Impossible de parser une suite valide depuis l'agent. "
                    f"Dernière réponse: {preview_a}"
                )
                return

            # Si thème nouveau, l'ajouter à la liste des thèmes
            if theme_pattern and self.memory and hasattr(self.memory, "add_theme_pattern"):
                try:
                    existing = self.memory.list_theme_patterns()
                    if theme_pattern not in existing:
                        self.memory.add_theme_pattern(theme_pattern)
                        logger.info(f"📚 [PATTERNS] Nouveau thème ajouté: {theme_pattern}")
                    else:
                        logger.debug(f"ℹ️  [PATTERNS] Thème existant utilisé: {theme_pattern}")
                except Exception as e:
                    logger.debug(f"ℹ️  [PATTERNS] Ajout thème ignoré: {e}")

            original_parsed = list(parsed)
            parsed = self._filter_valid_pattern_sequence(parsed)
            if not parsed:
                logger.warning(
                    f"⚠️  [PATTERNS] Suite parsée non exécutable dans l'automate: {original_parsed}"
                )
                return
            if parsed != original_parsed:
                logger.info(
                    f"ℹ️  [PATTERNS] Suite ajustée pour transitions: "
                    f"avant={original_parsed}, après={parsed}"
                )

            logger.info(
                f"✅ [PATTERNS] Suite recommandée par l'AGENT (parsée et valide): "
                f"{[[theme_pattern], *parsed] if theme_pattern else parsed}"
            )

        # Apprendre toutes les transitions de la suite (ctx, prev_step) -> next_step
        # Important: on ne veut pas seulement prev=initial. Sinon on retombe sur l'agent après le 1er choix.
        prev_step = "initial"
        for i, code in enumerate(parsed):
            ctx = "base" if code.startswith("B") else "general"
            ctx_prefix = "B" if ctx == "base" else "G"

            # Suffixe contigu dans le même menu (jusqu'au changement de contexte)
            suffix: List[str] = []
            j = i
            while j < len(parsed) and parsed[j].startswith(ctx_prefix):
                suffix.append(parsed[j])
                j += 1

            if not suffix:
                prev_step = code
                continue

            weights = self._compute_order_weights(suffix)
            recommended_step = suffix[0]

            try:
                try:
                    prev_state = self.memory.get_pattern_recommendation(
                        menu_context=ctx,
                        prev_step=prev_step,
                    )
                    logger.info(f"🔎 [PATTERNS] État AVANT upsert (ctx={ctx}, prev={prev_step}): {prev_state}")
                except Exception:
                    prev_state = None

                pid = self.memory.upsert_pattern(
                    menu_context=ctx,
                    prev_step=prev_step,
                    recommended_step=recommended_step,
                    weights=weights,
                    source="gemini",
                    confidence=0.9,
                    theme_pattern=theme_pattern,
                )

                try:
                    new_state = self.memory.get_pattern_recommendation(
                        menu_context=ctx,
                        prev_step=prev_step,
                    )
                except Exception:
                    new_state = None

                logger.info(
                    f"📚 [PATTERNS] Pattern mis à jour via AGENT: theme={theme_pattern or 'global'}, "
                    f"ctx={ctx}, prev={prev_step}, rec={recommended_step}, id={pid}, "
                    f"weights={weights}, avant={prev_state}, apres={new_state}"
                )
            except Exception as e:
                logger.warning(f"⚠️  [PATTERNS] Erreur lors de l'upsert pattern (ctx={ctx}, prev={prev_step}): {e}")

            prev_step = code

    async def learn_patterns_from_last(self) -> None:
        """Point d'entrée public pour lancer l'apprentissage patterns après coup (depuis app_chat).

        Utilise le dernier plan + requête mémorisés par generate_with_trace().
        """
        try:
            if not self._last_patterns_plan or not self._last_patterns_request:
                logger.info("ℹ️  [PATTERNS] Aucun contexte patterns disponible (pas de plan récent).")
                return
            await self._learn_menu_patterns_with_agent(
                user_request=self._last_patterns_request,
                plan=self._last_patterns_plan,
            )
        except Exception as e:
            logger.warning(f"⚠️  [PATTERNS] Erreur dans learn_patterns_from_last: {e}")

    def _clean_response(self, response: str) -> str:
        """
        Nettoie la réponse générée.
        
        Distingue entre :
        - Questions légitimes que LIA pose à l'utilisateur (à préserver)
        - Interactions fictives avec "Utilisateur :" ou "LIA :" (à supprimer)
        - Sections techniques (### Définition, etc.) (à supprimer)
        """
        # Marqueurs à détecter pour arrêter le nettoyage (interactions fictives)
        # Ces patterns indiquent que LIA invente des interactions
        stop_markers = [
            "Utilisateur :",  # Format d'interaction fictive
            "Utilisateur:",   # Format d'interaction fictive
            "=== Conversation",  # Nouvelle section de conversation
            "=== CONVERSATION",
            # Sections méta / structure de prompt qui ne doivent jamais sortir dans la réponse
            "=== PRINCIPES",
            "PRINCIPES GUIDANT",
            "### ÉCHANGE",
            "### ECHANGE",
            "=== ÉCHANGE",
            "=== ECHANGE",
            # Échos possibles de sections système
            "=== MON ENVIRONNEMENT ===",
            "=== QUI JE SUIS ===",
            "=== MES SOUVENIRS ===",
            "=== MES OBJECTIFS ===",
            "=== HISTORIQUE",
            "=== FIN DE L'HISTORIQUE ===",
            "### Définition",  # Section technique
            "### Fonctionnement",  # Section technique
            "### Types",  # Section technique
            "[Échange précédent",  # Référence à un échange fictif
            "Échange précédent",
            "Voici les réponses",  # Format technique
            "Réponse :",  # Format technique (pas une question)
            "Question :",  # Format technique (pas une question)
            "LIA se tourne",  # Narration fictive
            "LIA écrit",  # Narration fictive
            "LIA décide",  # Narration fictive
            "Session en cours:",  # Fragment de contexte mémoire
            "Je m'apelle:",  # Fragment d'identité
            "Je m'appelle:",  # Fragment d'identité
            "l'une des entités",  # Fragment de contexte
        ]
        
        # Trouver le premier marqueur d'arrêt (interaction fictive)
        lines = response.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # Vérifier si on a atteint un marqueur d'interaction fictive
            # Pattern: "Utilisateur : [texte]" ou "LIA : [texte]" au début de ligne
            if re.match(r'^(Utilisateur|LIA|Assistant)\s*:\s*', line.strip(), flags=re.IGNORECASE):
                logger.debug(f"⚠️  Arrêt du nettoyage (interaction fictive): {line[:50]}...")
                break
            
            # Vérifier les autres marqueurs d'arrêt
            if any(marker in line for marker in stop_markers):
                logger.debug(f"⚠️  Arrêt du nettoyage à: {line[:50]}...")
                break
            
            # Vérifier si on a atteint une nouvelle section de conversation
            if "=== Conversation" in line:
                logger.debug(f"⚠️  Arrêt du nettoyage (nouvelle section): {line[:50]}...")
                break
            
            cleaned_lines.append(line)
        
        response = "\n".join(cleaned_lines)
        
        # Supprimer les marqueurs de section techniques qui pourraient apparaître
        # MAIS préserver les questions normales (qui peuvent contenir "?" ou "tu")
        markers_to_remove = [
            "=== Personnalité ===", "=== Souvenirs ===", "=== Objectifs ===",
            "=== Conversation ===", "=== CONVERSATION ACTUELLE ===",
            "=== MON ENVIRONNEMENT ===", "=== QUI JE SUIS ===", "=== MES SOUVENIRS ===", "=== MES OBJECTIFS ===",
            "=== HISTORIQUE DE NOTRE CONVERSATION ===", "=== FIN DE L'HISTORIQUE ===",
            "=== PRINCIPES GUIDANT LA CONVERSATION ===",
            "### ÉCHANGE ACTUEL", "### ECHANGE ACTUEL",
            "### Définition", "### Fonctionnement", "### Types",
            "[Échange précédent", "Voici les réponses",
        ]
        
        for marker in markers_to_remove:
            response = response.replace(marker, "")
        
        # Supprimer les interactions fictives (format "Utilisateur : [texte]" ou "LIA : [texte]")
        # Mais préserver les questions normales dans le texte
        response = re.sub(r'^(Utilisateur|LIA|Assistant)\s*:\s*', '', response, flags=re.MULTILINE | re.IGNORECASE)
        
        # Supprimer les références aux échanges précédents
        response = re.sub(r'\[Échange précédent \d+\]', '', response)
        response = re.sub(r'Échange précédent \d+', '', response)
        
        # Supprimer les formats techniques "Réponse :" ou "Question :" (sauf si c'est une vraie question)
        # Pattern: "Réponse :" ou "Question :" suivi d'un texte (format technique)
        response = re.sub(r'^(Réponse|Question)\s*:\s*', '', response, flags=re.MULTILINE)
        
        # Supprimer les fragments de contexte mémoire
        response = re.sub(r'Session en cours:.*?(?=\n|$)', '', response, flags=re.MULTILINE)
        response = re.sub(r"Je m'apelle:.*?(?=\n|$)", '', response, flags=re.MULTILINE)
        response = re.sub(r"Je m'appelle:.*?(?=\n|$)", '', response, flags=re.MULTILINE)
        response = re.sub(r"l'une des entités.*?(?=\n|$)", '', response, flags=re.MULTILINE)
        
        # Supprimer les numéros de liste isolés (1., 2., 3., etc.) au début de lignes
        response = re.sub(r'^\d+\.\s*', '', response, flags=re.MULTILINE)
        
        # Supprimer les fragments qui commencent par des numéros suivis de texte technique
        # Pattern: "2. Je m'apelle:" ou "3. Session en cours:"
        response = re.sub(r'\d+\.\s*(Je m\'?apelle|Session en cours|l\'une des entités).*?(?=\n|$)', '', response, flags=re.MULTILINE | re.IGNORECASE)
        
        # Supprimer les répétitions excessives
        lines = response.split("\n")
        cleaned_lines = []
        seen = set()
        
        for line in lines:
            line_stripped = line.strip()
            # Préserver les lignes vides et les questions (qui peuvent être répétées légitimement)
            if not line_stripped or line_stripped not in seen or '?' in line_stripped:
                cleaned_lines.append(line)
                if line_stripped:
                    seen.add(line_stripped)
        
        response = "\n".join(cleaned_lines)
        
        # Supprimer un numéro parasite en fin de phrase (ex: "Qu'est-ce que tu veux savoir? 2.")
        response = re.sub(r'\s+\d+\.\s*$', '', response.strip())

        # Nettoyer les espaces multiples
        response = re.sub(r'\n{3,}', '\n\n', response)
        response = re.sub(r' {2,}', ' ', response)
        
        return response.strip()
    
    def update_config(self, **kwargs) -> None:
        """
        Met à jour la configuration (pour auto-calibration).
        
        Args:
            **kwargs: Paramètres à mettre à jour
        """
        if not self.config.enable_auto_calibration:
            logger.warning("Auto-calibration désactivée")
            return
        
        self.config.update(**kwargs)
        logger.info(f"Configuration mise à jour: {kwargs}")

