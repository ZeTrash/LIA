"""Interface web pour converser avec LIA."""

import asyncio
import json
import sys
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from interfaces import UserChannel
from core import CoreConfig
from support import SupportChannel, SupportConfig, GeminiAdapter
from memory_service import MemoryAdapter
from core import AutonomyBrain, AutonomyScheduler

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LIA - Interface de Chat")

# Defaults alignés sur docs/last_docs_update/LIA_ARCHITECTURE_V2.md
DOC_DEFAULT_BACKEND = "vllm"
DOC_DEFAULT_LANG_MODEL = "Qwen/Qwen2.5-72B-Instruct"
DOC_DEFAULT_ROUTER_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DOC_DEFAULT_CODE_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"

# Dossier pour les fichiers statiques
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

# Instance globale du canal utilisateur
user_channel: Optional[UserChannel] = None
autonomy_scheduler: Optional[AutonomyScheduler] = None


class ConnectionManager:
    """Gère les connexions WebSocket."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"✅ Connexion établie: session {session_id[:8]}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"❌ Connexion fermée: session {session_id[:8]}")
    
    async def send_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for websocket in self.active_connections.values():
            await websocket.send_json(message)


manager = ConnectionManager()

PATTERN_BRAIN_BASE_URL = os.getenv("LIA_PATTERN_BRAIN_BASE_URL", "http://127.0.0.1:8002")
PATTERN_BRAIN_HEALTH_URL = f"{PATTERN_BRAIN_BASE_URL}/health"
SYSTEM_EVENTS_LOG_PATH = Path(__file__).parent.parent / "logs" / "lia_system_events.jsonl"

def _autonomy_event_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "autonomy_event",
        "event": event,
        "timestamp": event.get("timestamp") or datetime.now().isoformat(),
    }


async def _ensure_autonomy_scheduler() -> AutonomyScheduler:
    global autonomy_scheduler
    if autonomy_scheduler is not None:
        return autonomy_scheduler

    async def _codebrain_action(spec: str) -> Dict[str, Any]:
        # Appel direct du cycle self-improvement du core adapter.
        core = await _get_core_adapter()
        if not hasattr(core, "_run_self_improvement_cycle"):
            return {"success": False, "reason": "core self-improvement unavailable"}
        message = f"Auto amélioration: recode toi pour {spec}"
        response = await core._run_self_improvement_cycle(message, session_id="autonomy_loop")
        text = str(response or "")
        success = "appliquée" in text.lower() or "applied" in text.lower()
        return {"success": success, "response": text}

    brain = AutonomyBrain(code_action_callback=_codebrain_action)
    autonomy_scheduler = AutonomyScheduler(
        brain=brain,
        on_event=lambda ev: manager.broadcast(_autonomy_event_payload(ev)),
    )
    return autonomy_scheduler


def start_pattern_brain_subprocess() -> None:
    """Lance le service pattern-brain dans un process séparé (si activé)."""
    auto = os.getenv("LIA_AUTO_START_PATTERN_BRAIN", "1").lower() in {"1", "true", "yes", "oui"}
    if not auto:
        logger.info("ℹ️  Auto-start du service pattern-brain désactivé (LIA_AUTO_START_PATTERN_BRAIN=0).")
        return

    try:
        project_root = Path(__file__).parent.parent
        python_exe = sys.executable or "python3"
        cmd = [
            python_exe,
            "-m",
            "support.pattern_brain_service",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
        ]
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "pattern_brain.log"
        with open(log_file, "a") as f:
            f.write(f"\n--- Démarrage {datetime.now().isoformat()} ---\n")
        subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
        )
        logger.info("🚀 Service pattern-brain lancé en arrière-plan sur http://127.0.0.1:8002 (logs: %s)", log_file)
    except Exception as e:
        logger.warning(f"⚠️  Impossible de lancer automatiquement le service pattern-brain: {e}")


async def ensure_pattern_brain_ready(timeout_s: float = 90.0) -> None:
    """S'assure que le service pattern-brain est lancé et prêt (modèle chargé)."""
    auto = os.getenv("LIA_AUTO_START_PATTERN_BRAIN", "1").lower() in {"1", "true", "yes", "oui"}
    if not auto:
        return

    try:
        import httpx
    except Exception:
        logger.warning("⚠️  httpx indisponible: impossible de vérifier l'état du pattern-brain.")
        start_pattern_brain_subprocess()
        return

    async def _is_ready() -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(PATTERN_BRAIN_HEALTH_URL)
                r.raise_for_status()
                data = r.json()
                return bool(data.get("ready"))
        except Exception:
            return False

    # Déjà prêt ? ne rien faire.
    if await _is_ready():
        logger.info("✅ Service pattern-brain déjà prêt (%s).", PATTERN_BRAIN_HEALTH_URL)
        return

    # Sinon, démarrer le subprocess puis attendre qu'il devienne prêt.
    start_pattern_brain_subprocess()

    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        if await _is_ready():
            logger.info("✅ Service pattern-brain prêt (modèle chargé).")
            return
        await asyncio.sleep(1.0)

    logger.warning(
        "⚠️  Service pattern-brain non prêt après %.0f s. "
        "Il charge peut-être encore le modèle; les appels patterns feront des retries.",
        timeout_s,
    )


async def support_stream_callback(event: str, payload: Dict[str, Any]) -> None:
    """Callback utilisé par SupportChannel pour streamer les étapes Gemini en temps réel."""
    session_id = payload.get("session_id")
    if not session_id:
        return

    timestamp = payload.get("timestamp", datetime.now().isoformat())

    # Démarrage du processus + question envoyée à Gemini
    if event == "gemini_query":
        await manager.send_message({
            "type": "process_start",
            "content": "LIA décide de solliciter Gemini pour obtenir plus d'informations",
            "timestamp": timestamp,
        }, session_id)

        question = payload.get("question", "")
        if question:
            await manager.send_message({
                "type": "gemini_query",
                "content": question,
                "timestamp": timestamp,
            }, session_id)
        
        # Créer un message pour la réponse streaming
        await manager.send_message({
            "type": "gemini_response_start",
            "content": "",
            "timestamp": timestamp,
        }, session_id)

    # Chunk de réponse Gemini (streaming)
    elif event == "gemini_chunk":
        chunk = payload.get("chunk", "")
        if chunk:
            await manager.send_message({
                "type": "gemini_chunk",
                "content": chunk,
                "timestamp": timestamp,
            }, session_id)

    # Réponse ou erreur Gemini + fin du processus
    elif event in ("gemini_response", "gemini_error"):
        is_error = event == "gemini_error" or not payload.get("success", True)

        if is_error:
            error_msg = payload.get("error") or "Gemini n'a pas pu répondre."
            await manager.send_message({
                "type": "gemini_error",
                "content": f"Gemini n'a pas pu répondre: {error_msg}",
                "timestamp": timestamp,
            }, session_id)
        else:
            answer = payload.get("answer", "")
            if answer:
                # Si on n'a pas utilisé le streaming, envoyer la réponse complète
                await manager.send_message({
                    "type": "gemini_response_end",
                    "content": "",
                    "timestamp": timestamp,
                }, session_id)

        # Fin de processus
        await manager.send_message({
            "type": "process_end",
            "content": "LIA a intégré les informations de Gemini",
            "timestamp": timestamp,
        }, session_id)


async def initialize_user_channel():
    """Initialise le canal utilisateur."""
    global user_channel
    
    if user_channel is not None:
        return user_channel
    
    logger.info("🔧 Initialisation du canal utilisateur...")
    
    try:
        # Configuration du noyau primaire
        # Par défaut: utiliser strictement les valeurs "doc V2".
        # Les overrides d'environnement sont opt-in via LIA_USE_ENV_MODEL_OVERRIDES=1.
        use_env_model_overrides = os.getenv("LIA_USE_ENV_MODEL_OVERRIDES", "0").strip().lower() in {"1", "true", "yes", "oui"}

        llm_backend = DOC_DEFAULT_BACKEND
        llm_model_name = DOC_DEFAULT_LANG_MODEL
        llm_router_model = DOC_DEFAULT_ROUTER_MODEL
        llm_lang_model = DOC_DEFAULT_LANG_MODEL
        llm_code_model = DOC_DEFAULT_CODE_MODEL

        if use_env_model_overrides:
            llm_backend = os.getenv("LIA_LLM_BACKEND", llm_backend).strip().lower()
            llm_model_name = os.getenv("LIA_LLM_MODEL", llm_model_name).strip()
            llm_router_model = os.getenv("LIA_ROUTER_MODEL", llm_router_model).strip()
            llm_lang_model = os.getenv("LIA_LANG_MODEL", llm_lang_model).strip()
            llm_code_model = os.getenv("LIA_CODE_MODEL", llm_code_model).strip()
            logger.info("ℹ️  Overrides modèles via env activés (LIA_USE_ENV_MODEL_OVERRIDES=1).")
        else:
            if any(
                os.getenv(k)
                for k in ("LIA_LLM_BACKEND", "LIA_LLM_MODEL", "LIA_ROUTER_MODEL", "LIA_LANG_MODEL", "LIA_CODE_MODEL")
            ):
                logger.warning(
                    "⚠️  Variables LIA_*_MODEL détectées mais ignorées "
                    "(utilisation des defaults doc V2). "
                    "Définir LIA_USE_ENV_MODEL_OVERRIDES=1 pour les activer."
                )

        llm_max_length = int(os.getenv("LIA_LLM_MAX_LENGTH", "15360"))
        llm_temperature = float(os.getenv("LIA_LLM_TEMPERATURE", "0.8"))
        llm_vllm_max_len = int(os.getenv("LIA_VLLM_MAX_MODEL_LEN", "32768"))
        llm_vllm_dtype = os.getenv("LIA_VLLM_DTYPE", "float16").strip()
        llm_vllm_gpu_mem = float(os.getenv("LIA_VLLM_GPU_MEMORY_UTILIZATION", "0.75"))
        llm_enable_self_improvement = os.getenv("LIA_ENABLE_SELF_IMPROVEMENT", "1").strip().lower() in {"1", "true", "yes", "oui"}
        llm_require_human_approval_self_mod = os.getenv("LIA_REQUIRE_HUMAN_APPROVAL_SELF_MOD", "0").strip().lower() in {"1", "true", "yes", "oui"}
        llm_autonomy_mode = os.getenv("LIA_AUTONOMY_MODE", "auto_with_audit").strip().lower()
        llm_autonomy_min_plan_conf = float(os.getenv("LIA_AUTONOMY_MIN_PLAN_CONFIDENCE", "0.55"))
        llm_autonomy_min_prompt_conf = float(os.getenv("LIA_AUTONOMY_MIN_PROMPT_CONFIDENCE", "0.55"))
        llm_autonomy_max_replans = int(os.getenv("LIA_AUTONOMY_MAX_REPLANS", "2"))
        llm_autonomy_max_prompt_rebuilds = int(os.getenv("LIA_AUTONOMY_MAX_PROMPT_REBUILDS", "1"))

        use_env_backend = llm_backend in {"vllm", "transformers"}
        if use_env_backend:
            core_config = CoreConfig(
                model_name=llm_model_name,
                backend=llm_backend,
                use_gguf=False,
                max_length=llm_max_length,
                temperature=llm_temperature,
                vllm_max_model_len=llm_vllm_max_len,
                vllm_dtype=llm_vllm_dtype,
                vllm_gpu_memory_utilization=llm_vllm_gpu_mem,
                router_model=llm_router_model,
                lang_model=llm_lang_model,
                code_model=llm_code_model,
                enable_code_brain=True,
                enable_neural_router=True,
                enable_real_brain_routing=True,
                enable_self_improvement=llm_enable_self_improvement,
                require_human_approval_for_self_mod=llm_require_human_approval_self_mod,
                autonomy_mode=llm_autonomy_mode,
                autonomy_min_plan_confidence=llm_autonomy_min_plan_conf,
                autonomy_prompt_min_confidence=llm_autonomy_min_prompt_conf,
                autonomy_max_replans=llm_autonomy_max_replans,
                autonomy_max_prompt_rebuilds=llm_autonomy_max_prompt_rebuilds,
            )
            logger.info(
                "✅ Backend LLM via environnement: backend=%s, router=%s, lang=%s, code=%s",
                llm_backend,
                llm_router_model,
                llm_lang_model,
                llm_code_model,
            )
        else:
            # Utiliser un chemin absolu pour le modèle GGUF (préférer Qwen2.5-7B si disponible)
            project_root = Path(__file__).parent.parent.resolve()
            qwen_path = project_root / "models" / "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
            llama_path = project_root / "models" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
            gguf_model_path = qwen_path if qwen_path.exists() else llama_path

            # Vérifier que le modèle existe
            if not gguf_model_path.exists():
                logger.warning(f"⚠️  Modèle GGUF non trouvé: {gguf_model_path}")
                logger.warning("   Utilisation du modèle par défaut (Qwen)")
                core_config = CoreConfig(
                    use_gguf=False,  # Désactiver GGUF si le modèle n'existe pas
                    max_length=512,
                    temperature=0.8,
                    enable_neural_router=True,
                    enable_self_improvement=llm_enable_self_improvement,
                    require_human_approval_for_self_mod=llm_require_human_approval_self_mod,
                    autonomy_mode=llm_autonomy_mode,
                    autonomy_min_plan_confidence=llm_autonomy_min_plan_conf,
                    autonomy_prompt_min_confidence=llm_autonomy_min_prompt_conf,
                    autonomy_max_replans=llm_autonomy_max_replans,
                    autonomy_max_prompt_rebuilds=llm_autonomy_max_prompt_rebuilds,
                )
            else:
                logger.info(f"✅ Modèle GGUF trouvé: {gguf_model_path.name}")
                core_config = CoreConfig(
                    use_gguf=True,
                    gguf_model_path=str(gguf_model_path.resolve()),  # Chemin absolu
                    max_length=512,
                    temperature=0.8,
                    enable_neural_router=True,
                    enable_self_improvement=llm_enable_self_improvement,
                    require_human_approval_for_self_mod=llm_require_human_approval_self_mod,
                    autonomy_mode=llm_autonomy_mode,
                    autonomy_min_plan_confidence=llm_autonomy_min_plan_conf,
                    autonomy_prompt_min_confidence=llm_autonomy_min_prompt_conf,
                    autonomy_max_replans=llm_autonomy_max_replans,
                    autonomy_max_prompt_rebuilds=llm_autonomy_max_prompt_rebuilds,
                )
        
        # Initialiser la mémoire
        memory = MemoryAdapter()
        logger.info("✅ Mémoire initialisée")
        
        # Optionnel : créer le canal Support pour l'autonomie
        support_channel = None
        try:
            support_config = SupportConfig()
            config_path = Path(__file__).parent.parent / "config" / "api.conf"
            if config_path.exists():
                support_config.load_from_file(str(config_path))
                # Préférer Groq si disponible, sinon Gemini
                groq_adapter = None
                gemini_adapter = None
                if support_config.groq_api_key and support_config.groq_api_key != "YOUR_GROQ_API_KEY_HERE":
                    from support.groq_adapter import GroqAdapter
                    groq_adapter = GroqAdapter(support_config)
                    logger.info("✅ GroqAdapter créé (préféré pour les patterns)")
                if support_config.gemini_api_key and support_config.gemini_api_key != "YOUR_GEMINI_API_KEY_HERE":
                    gemini_adapter = GeminiAdapter(support_config)
                
                if groq_adapter or gemini_adapter:
                    support_channel = SupportChannel(
                        groq_adapter=groq_adapter,
                        gemini_adapter=gemini_adapter,
                        memory_adapter=memory,
                        config=support_config
                    )
                    # Activer le streaming temps réel des étapes vers l'interface web
                    if hasattr(support_channel, "set_stream_callback"):
                        support_channel.set_stream_callback(support_stream_callback)
                    adapter_name = "Groq" if groq_adapter else "Gemini"
                    logger.info(f"✅ Canal Support créé avec {adapter_name} (autonomie activée)")
                else:
                    logger.warning("⚠️  Aucune clé API configurée (Groq/Gemini) - autonomie désactivée")
            else:
                logger.warning("⚠️  Fichier de configuration non trouvé - autonomie désactivée")
        except Exception as e:
            logger.warning(f"⚠️  Canal Support non disponible: {e}")
            logger.warning("   Le canal utilisateur fonctionnera sans autonomie")
        
        # Créer le canal utilisateur
        user_channel = UserChannel(
            memory_adapter=memory,
            support_channel=support_channel,
            core_config=core_config
        )
        
        logger.info("✅ Canal utilisateur initialisé")
        return user_channel
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}")
        raise


async def _get_core_adapter():
    if user_channel is None:
        await initialize_user_channel()
    core = getattr(user_channel, "core_adapter", None)
    if core is None:
        raise HTTPException(status_code=503, detail="Core adapter indisponible")
    return core


def _normalize_pending_payload(pending: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not pending:
        return {"has_pending": False, "target_module": None}
    return {
        "has_pending": bool(pending.get("has_proposal")),
        "target_module": pending.get("target_module"),
    }


async def _emit_self_mod_pending_changed(session_id: Optional[str] = None) -> None:
    """Push websocket de l'état pending self-mod (session ciblée ou broadcast)."""
    try:
        core = await _get_core_adapter()
        pending = core.get_pending_self_modification() if hasattr(core, "get_pending_self_modification") else None
        payload = {
            "type": "self_mod_pending_changed",
            "pending": _normalize_pending_payload(pending),
            "timestamp": datetime.now().isoformat(),
        }
        if session_id:
            await manager.send_message(payload, session_id)
        else:
            await manager.broadcast(payload)
    except Exception as e:
        logger.debug(f"Emission self_mod_pending_changed ignorée: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialise le canal utilisateur au démarrage."""
    # Lancer le noyau subconscient (pattern-brain) en arrière-plan
    await ensure_pattern_brain_ready()
    await initialize_user_channel()
    await _ensure_autonomy_scheduler()


@app.get("/")
async def get_index():
    """Page principale du chat."""
    html_file = static_dir / "chat.html"
    if html_file.exists():
        return FileResponse(html_file)
    
    # Fallback HTML simple
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LIA - Chat</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <h1>LIA - Interface de Chat</h1>
        <p>Le fichier chat.html n'a pas été trouvé. Veuillez créer le fichier dans static/chat.html</p>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Vérifie l'état du service."""
    return {
        "status": "ok",
        "user_channel_initialized": user_channel is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/brains")
async def health_brains():
    """Expose l'état runtime des brains (Router/Lang/Code)."""
    if user_channel is None:
        await initialize_user_channel()

    core = getattr(user_channel, "core_adapter", None)
    if core is None:
        raise HTTPException(status_code=503, detail="Core adapter indisponible")

    cfg = getattr(core, "config", None)
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "backend": getattr(core, "backend_type", "unknown"),
        "brains": {
            "neural_router_enabled": bool(getattr(cfg, "enable_neural_router", False)),
            "real_brain_routing_enabled": bool(getattr(cfg, "enable_real_brain_routing", False)),
            "code_brain_enabled": bool(getattr(cfg, "enable_code_brain", False)),
            "vision_brain_enabled": bool(getattr(cfg, "enable_vision_brain", False)),
            "audio_brain_enabled": bool(getattr(cfg, "enable_audio_brain", False)),
            "router_brain_loaded": getattr(core, "router_brain_model", None) is not None,
            "code_brain_loaded": getattr(core, "code_brain", None) is not None,
            "vision_brain_loaded": getattr(core, "vision_brain", None) is not None,
            "audio_brain_loaded": getattr(core, "audio_brain", None) is not None,
            "interoception_enabled": getattr(core, "interoception_brain", None) is not None,
        },
        "models": {
            "router_model": getattr(cfg, "router_model", None),
            "lang_model": getattr(cfg, "lang_model", None),
            "code_model": getattr(cfg, "code_model", None),
        },
    }


def _compute_runtime_kpis_from_events() -> Dict[str, Any]:
    auto_count = 0
    menu_count = 0
    exchange_end_count = 0
    self_mod_attempts = 0
    self_mod_success = 0
    if not SYSTEM_EVENTS_LOG_PATH.exists():
        return {
            "auto_path_rate": 0.0,
            "menu_fallback_rate": 0.0,
            "self_mod_accept_rate": 0.0,
            "events_processed": 0,
        }
    try:
        with SYSTEM_EVENTS_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception:
                    continue
                name = str(evt.get("event", ""))
                payload = evt.get("payload", {}) or {}
                if name == "exchange_end":
                    exchange_end_count += 1
                    stop_reason = str(payload.get("stop_reason", ""))
                    if stop_reason == "auto_plan":
                        auto_count += 1
                    else:
                        menu_count += 1
                if name in {
                    "self_improvement_sandbox_result",
                    "self_improvement_applied",
                    "self_improvement_applied_after_approval",
                }:
                    self_mod_attempts += 1
                if name in {"self_improvement_applied", "self_improvement_applied_after_approval"}:
                    self_mod_success += 1
    except Exception:
        return {
            "auto_path_rate": 0.0,
            "menu_fallback_rate": 0.0,
            "self_mod_accept_rate": 0.0,
            "events_processed": 0,
        }
    auto_rate = (auto_count / exchange_end_count) if exchange_end_count else 0.0
    menu_rate = (menu_count / exchange_end_count) if exchange_end_count else 0.0
    self_mod_rate = (self_mod_success / self_mod_attempts) if self_mod_attempts else 0.0
    return {
        "auto_path_rate": round(auto_rate, 4),
        "menu_fallback_rate": round(menu_rate, 4),
        "self_mod_accept_rate": round(self_mod_rate, 4),
        "events_processed": exchange_end_count,
    }


@app.get("/health/interoception")
async def health_interoception():
    """Expose un rapport health interne de type InteroceptionBrain."""
    core = await _get_core_adapter()
    intero = getattr(core, "interoception_brain", None)
    if intero is None:
        raise HTTPException(status_code=503, detail="InteroceptionBrain indisponible")
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "interoception": intero.get_health_report(),
    }


@app.get("/health/kpis")
async def health_kpis():
    """Expose des KPIs V2 d'autonomie/fallback basés sur les événements."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "kpis": _compute_runtime_kpis_from_events(),
    }


@app.get("/autonomy/status")
async def autonomy_status():
    """Retourne l'état du scheduler + snapshot d'état autonome."""
    scheduler = await _ensure_autonomy_scheduler()
    st = scheduler.status()
    state = scheduler.brain.get_state().to_dict()
    recent_cycles = scheduler.brain.store.list_recent_cycles(limit=10)
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "autonomy": st.__dict__,
        "state": state,
        "recent_cycles": recent_cycles,
    }


@app.post("/autonomy/start")
async def autonomy_start(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Démarre la boucle autonome (scheduler continu)."""
    scheduler = await _ensure_autonomy_scheduler()
    interval_s = float(payload.get("interval_s") or 60.0)
    st = await scheduler.start(interval_seconds=interval_s)
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "autonomy": st.__dict__,
    }


@app.post("/autonomy/stop")
async def autonomy_stop(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Stoppe la boucle autonome."""
    scheduler = await _ensure_autonomy_scheduler()
    st = await scheduler.stop()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "autonomy": st.__dict__,
    }


@app.post("/autonomy/cycle")
async def autonomy_cycle_once():
    """Exécute un cycle autonome immédiat (debug/supervision)."""
    scheduler = await _ensure_autonomy_scheduler()
    payload = await scheduler.run_single_cycle()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "cycle": payload,
    }


@app.post("/autonomy/inject/trait")
async def autonomy_inject_trait(payload: Dict[str, Any] = Body(default_factory=dict)):
    scheduler = await _ensure_autonomy_scheduler()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name requis")
    intensity = float(payload.get("intensity", 0.7))
    category = str(payload.get("category") or "injected")
    result = scheduler.brain.inject_trait(name=name, intensity=intensity, category=category)
    await manager.broadcast(_autonomy_event_payload(result))
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "result": result}


@app.post("/autonomy/inject/gauge")
async def autonomy_inject_gauge(payload: Dict[str, Any] = Body(default_factory=dict)):
    scheduler = await _ensure_autonomy_scheduler()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name requis")
    if "current" not in payload:
        raise HTTPException(status_code=400, detail="current requis")
    result = scheduler.brain.inject_gauge(
        name=name,
        current=float(payload.get("current")),
        decay_rate=payload.get("decay_rate"),
        low=payload.get("low"),
        critical_low=payload.get("critical_low"),
    )
    await manager.broadcast(_autonomy_event_payload(result))
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "result": result}


@app.post("/autonomy/inject/desire")
async def autonomy_inject_desire(payload: Dict[str, Any] = Body(default_factory=dict)):
    scheduler = await _ensure_autonomy_scheduler()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name requis")
    priority = float(payload.get("priority", 0.8))
    generating_trait = str(payload.get("generating_trait") or "injected")
    generating_gauge = payload.get("generating_gauge")
    result = scheduler.brain.inject_desire(
        name=name,
        priority=priority,
        generating_trait=generating_trait,
        generating_gauge=generating_gauge,
    )
    await manager.broadcast(_autonomy_event_payload(result))
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "result": result}


@app.post("/autonomy/inject/dream")
async def autonomy_inject_dream(payload: Dict[str, Any] = Body(default_factory=dict)):
    scheduler = await _ensure_autonomy_scheduler()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name requis")
    progress = float(payload.get("progress", 0.0))
    intensity = float(payload.get("intensity", 0.8))
    result = scheduler.brain.inject_dream(name=name, progress=progress, intensity=intensity)
    await manager.broadcast(_autonomy_event_payload(result))
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "result": result}


@app.post("/autonomy/inject/life-event")
async def autonomy_inject_life_event(payload: Dict[str, Any] = Body(default_factory=dict)):
    scheduler = await _ensure_autonomy_scheduler()
    event_type = str(payload.get("event_type") or "").strip()
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type requis")
    gauge_deltas = payload.get("gauge_deltas")
    trait_deltas = payload.get("trait_deltas")
    if gauge_deltas is not None and not isinstance(gauge_deltas, dict):
        raise HTTPException(status_code=400, detail="gauge_deltas doit être un objet")
    if trait_deltas is not None and not isinstance(trait_deltas, dict):
        raise HTTPException(status_code=400, detail="trait_deltas doit être un objet")
    result = scheduler.brain.inject_life_event(
        event_type=event_type,
        gauge_deltas=gauge_deltas,
        trait_deltas=trait_deltas,
    )
    await manager.broadcast(_autonomy_event_payload(result))
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "result": result}


@app.get("/autonomy/life-events")
async def autonomy_life_events():
    scheduler = await _ensure_autonomy_scheduler()
    presets = scheduler.brain.list_life_event_presets()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "life_events": presets,
    }


@app.get("/self-improvement/pending")
async def get_pending_self_improvement():
    """Retourne l'état de proposition d'auto-modification en attente."""
    core = await _get_core_adapter()
    pending = None
    if hasattr(core, "get_pending_self_modification"):
        pending = core.get_pending_self_modification()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "pending": pending,
    }


@app.post("/self-improvement/approve")
async def approve_self_improvement(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Approuve la proposition en attente et applique la modification."""
    core = await _get_core_adapter()
    session_id = payload.get("session_id")
    if not hasattr(core, "approve_pending_self_modification"):
        raise HTTPException(status_code=400, detail="Self-improvement non disponible")
    result = core.approve_pending_self_modification(session_id=session_id)
    await _emit_self_mod_pending_changed()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }


@app.post("/self-improvement/reject")
async def reject_self_improvement(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Rejette la proposition en attente sans appliquer le patch."""
    core = await _get_core_adapter()
    reason = payload.get("reason", "rejected from web ui")
    session_id = payload.get("session_id")
    if not hasattr(core, "reject_pending_self_modification"):
        raise HTTPException(status_code=400, detail="Self-improvement non disponible")
    result = core.reject_pending_self_modification(reason=reason, session_id=session_id)
    await _emit_self_mod_pending_changed()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }


@app.post("/self-improvement/rollback")
async def rollback_self_improvement(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Rollback la dernière auto-modification appliquée."""
    core = await _get_core_adapter()
    session_id = payload.get("session_id")
    if not hasattr(core, "rollback_last_self_modification"):
        raise HTTPException(status_code=400, detail="Rollback self-improvement non disponible")
    result = core.rollback_last_self_modification(session_id=session_id)
    await _emit_self_mod_pending_changed()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }


@app.post("/self-improvement/rollback-version")
async def rollback_self_improvement_version(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Rollback vers une version sauvegardée (version_id)."""
    core = await _get_core_adapter()
    session_id = payload.get("session_id")
    version_id = payload.get("version_id")
    if not version_id:
        raise HTTPException(status_code=400, detail="version_id requis")
    if not hasattr(core, "rollback_self_modification_version"):
        raise HTTPException(status_code=400, detail="Rollback versionné non disponible")
    result = core.rollback_self_modification_version(version_id=str(version_id), session_id=session_id)
    await _emit_self_mod_pending_changed()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Endpoint WebSocket pour le chat."""
    await manager.connect(websocket, session_id)
    
    try:
        # Envoyer un message de bienvenue
        await manager.send_message({
            "type": "system",
            "content": "✅ Connecté à LIA. Vous pouvez commencer à converser.",
            "timestamp": datetime.now().isoformat()
        }, session_id)
        await _emit_self_mod_pending_changed(session_id=session_id)
        
        while True:
            # Recevoir le message de l'utilisateur
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                user_message = data.get("content", "").strip()
                
                if not user_message:
                    await manager.send_message({
                        "type": "error",
                        "content": "Le message ne peut pas être vide.",
                        "timestamp": datetime.now().isoformat()
                    }, session_id)
                    continue
                
                # Afficher le message de l'utilisateur
                await manager.send_message({
                    "type": "user_message",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                }, session_id)
                
                # Indiquer que LIA réfléchit
                await manager.send_message({
                    "type": "thinking",
                    "content": "LIA réfléchit...",
                    "timestamp": datetime.now().isoformat()
                }, session_id)
                
                try:
                    # Envoyer le message à LIA via le canal utilisateur
                    if user_channel is None:
                        await initialize_user_channel()
                    
                    # IMPORTANT:
                    # La génération GGUF peut être bloquante/CPU-bound. Si on la lance dans la même
                    # boucle d'événement, les messages "lia_process" n'arrivent qu'à la fin.
                    # Solution: exécuter la génération dans un thread + remonter les chunks via une queue.

                    main_loop = asyncio.get_running_loop()
                    process_queue: asyncio.Queue[dict] = asyncio.Queue()

                    async def _process_sender() -> None:
                        """Consomme la queue et envoie les chunks PROCESS au WebSocket immédiatement."""
                        while True:
                            item = await process_queue.get()
                            try:
                                if item.get("_type") == "_done":
                                    return
                                await manager.send_message(item, session_id)
                            finally:
                                process_queue.task_done()

                    sender_task = asyncio.create_task(_process_sender())

                    async def process_callback(chunk: dict):
                        """Callback appelé à chaque étape de processus (côté génération)."""
                        if not isinstance(chunk, dict):
                            return
                        if chunk.get("type") != "process":
                            return
                        process_content = chunk.get("content", "")
                        payload = {
                            "type": "lia_process",
                            "content": process_content,
                            "metadata": chunk.get("metadata", {}),
                            "timestamp": datetime.now().isoformat(),
                        }
                        logger.info(
                            f"🌐 [WEB] Queue chunk PROCESS (temps réel): "
                            f'"{process_content}"'
                        )
                        # Thread-safe: on pousse dans la queue de la loop principale.
                        main_loop.call_soon_threadsafe(process_queue.put_nowait, payload)

                    def _run_generation_in_thread() -> Dict[str, Any]:
                        """Exécute la génération dans un thread avec sa propre event loop."""
                        return asyncio.run(
                            user_channel.send_message_structured(
                                message=user_message,
                                session_id=session_id,
                                use_autonomy=True,
                                process_callback=process_callback,
                            )
                        )

                    # Lancer la génération hors de la loop principale pour ne pas bloquer le WebSocket.
                    result = await asyncio.to_thread(_run_generation_in_thread)

                    # Terminer proprement l'envoi des chunks process
                    await process_queue.put({"_type": "_done"})
                    await sender_task

                    # Afficher la réponse finale à l'utilisateur
                    final_response = result.get("lia_response") or ""

                    # Conserver le protocole existant (start / chunk / end) pour compatibilité front
                    await manager.send_message(
                        {
                            "type": "lia_response_start",
                            "content": "",
                            "timestamp": datetime.now().isoformat(),
                        },
                        session_id,
                    )
                        
                    await manager.send_message(
                        {
                            "type": "lia_chunk",
                            "content": final_response,
                            "timestamp": datetime.now().isoformat(),
                        },
                        session_id,
                    )
                    
                    await manager.send_message(
                        {
                            "type": "lia_response_end",
                            "content": "",
                            "interaction_id": result.get("interaction_id"),
                            "timestamp": result.get("timestamp"),
                            "success": result.get("success", True),
                        },
                        session_id,
                    )
                    await _emit_self_mod_pending_changed(session_id=session_id)

                    # Lancer l'apprentissage des patterns APRÈS envoi de la réponse, en tâche de fond
                    try:
                        core_adapter = getattr(user_channel, "core_adapter", None)
                        if core_adapter and hasattr(core_adapter, "learn_patterns_from_last"):
                            async def _run_patterns_bg():
                                try:
                                    await core_adapter.learn_patterns_from_last()
                                except Exception as pe:
                                    logger.warning(f"⚠️  [WEB] Erreur apprentissage patterns (background): {pe}")
                            asyncio.create_task(_run_patterns_bg())
                    except Exception as pe_outer:
                        logger.warning(f"⚠️  [WEB] Impossible de lancer learn_patterns_from_last: {pe_outer}")
                    
                except Exception as e:
                    logger.error(f"❌ Erreur lors de la génération: {e}")
                    await manager.send_message({
                        "type": "error",
                        "content": f"Erreur: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }, session_id)
                    await _emit_self_mod_pending_changed(session_id=session_id)
            
            elif data.get("type") == "get_history":
                # Récupérer l'historique de la session
                if user_channel is None:
                    await initialize_user_channel()
                
                history = user_channel.get_session_history(session_id)
                await manager.send_message({
                    "type": "history",
                    "content": history,
                    "timestamp": datetime.now().isoformat()
                }, session_id)
            
            elif data.get("type") == "get_stats":
                # Récupérer les statistiques
                if user_channel is None:
                    await initialize_user_channel()
                
                stats = user_channel.get_statistics()
                await manager.send_message({
                    "type": "stats",
                    "content": stats,
                    "timestamp": datetime.now().isoformat()
                }, session_id)
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"Client déconnecté: session {session_id[:8]}")
    except Exception as e:
        logger.error(f"❌ Erreur WebSocket: {e}")
        manager.disconnect(session_id)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Interface web de chat avec LIA")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse IP")
    parser.add_argument("--port", type=int, default=8001, help="Port")
    parser.add_argument("--reload", action="store_true", help="Mode reload (développement)")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "web_interface.app_chat:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

