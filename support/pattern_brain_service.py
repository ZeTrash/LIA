"""Service pattern-brain : noyau subconscient pour les recommandations de patterns.

Ce service tourne dans un process séparé et utilise son propre modèle LLM via LLMAdapter.
Le noyau principal l'appelle via HTTP (voir PATTERN_BRAIN_URL dans core.llm_adapter).

Lancer le service :
    cd /opt/LIA
    source venv/bin/activate
    python -m support.pattern_brain_service --host 127.0.0.1 --port 8002
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Assurer le PYTHONPATH correct
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import LLMAdapter, CoreConfig  # type: ignore


# Catalogue d'actions (doit rester cohérent avec core.llm_adapter.PATTERN_ACTIONS_CATALOG)
ACTIONS_CATALOG: Dict[str, str] = {
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


class PatternRequest(BaseModel):
    user_request: str
    executed_sequence: List[str]
    actions_catalog: Dict[str, str] | None = None


class PatternResponse(BaseModel):
    sequence: List[str]
    raw: str


app = FastAPI(title="LIA Pattern Brain Service")

# Instance globale (chargée au startup)
pattern_adapter: LLMAdapter | None = None


@app.on_event("startup")
async def startup_event() -> None:
    """Charge un LLMAdapter minimal pour le pattern-brain."""
    global pattern_adapter

    project_root = Path(__file__).parent.parent
    model_cache_dir = os.getenv("LIA_MODEL_CACHE_DIR", "models/hf_cache").strip()
    # Préférer Qwen2.5-7B si disponible, sinon fallback vers Llama-3.2-3B.
    qwen_path = project_root / "models" / "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    llama_path = project_root / "models" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    gguf_path = qwen_path if qwen_path.exists() else llama_path

    if gguf_path.exists():
        core_config = CoreConfig(
            use_gguf=True,
            gguf_model_path=str(gguf_path.resolve()),
            model_cache_dir=model_cache_dir,
            max_length=128,
            temperature=0.4,
            top_p=0.9,
            top_k=5,
        )
    else:
        # IMPORTANT:
        # Ne jamais hériter du LangBrain global (potentiellement 72B) ici.
        # Le pattern-brain doit rester léger et isolé.
        pattern_model = os.getenv("LIA_PATTERN_BRAIN_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
        pattern_device = os.getenv("LIA_PATTERN_BRAIN_DEVICE", "cuda").strip().lower()
        pattern_backend = os.getenv("LIA_PATTERN_BRAIN_BACKEND", "vllm").strip().lower()
        allow_heavy_pattern_model = os.getenv("LIA_PATTERN_BRAIN_ALLOW_HEAVY", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "oui",
        }

        # Garde-fou: éviter qu'un 72B soit chargé par erreur dans le pattern brain.
        # Pour l'autoriser, il faut un opt-in explicite via LIA_PATTERN_BRAIN_ALLOW_HEAVY=1.
        if ("72b" in pattern_model.lower() or "70b" in pattern_model.lower()) and not allow_heavy_pattern_model:
            print(
                "⚠️  [pattern_brain] modèle lourd détecté pour pattern brain, "
                f"fallback auto vers 7B: {pattern_model} -> Qwen/Qwen2.5-7B-Instruct"
            )
            pattern_model = "Qwen/Qwen2.5-7B-Instruct"

        if pattern_backend not in {"transformers", "vllm"}:
            pattern_backend = "vllm"
        core_config = CoreConfig(
            model_name=pattern_model,
            lang_model=pattern_model,
            backend=pattern_backend,
            device=pattern_device,
            use_gguf=False,
            quantize=False,
            model_cache_dir=model_cache_dir,
            vllm_max_model_len=8192,
            vllm_gpu_memory_utilization=0.20,
            max_length=128,
            temperature=0.4,
            top_p=0.9,
            top_k=5,
        )

    # Cache HF explicite pour éviter tout re-téléchargement entre redémarrages/services.
    cache_root = Path(core_config.model_cache_dir).resolve()
    hub_dir = cache_root / "hub"
    os.environ["HF_HOME"] = str(cache_root)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hub_dir)
    os.environ["TRANSFORMERS_CACHE"] = str(hub_dir)

    print(
        "[pattern_brain] config: "
        f"backend={core_config.backend}, device={core_config.device}, "
        f"model={core_config.model_name}, cache={core_config.model_cache_dir}, "
        f"vllm_max_model_len={core_config.vllm_max_model_len}, "
        f"vllm_gpu_memory_utilization={core_config.vllm_gpu_memory_utilization}"
    )

    # Adapter minimal : pas de mémoire, pas de planner
    pattern_adapter = LLMAdapter(
        config=core_config,
        use_memory=False,
        gemini_adapter=None,
        support_channel=None,
        use_cognitive_planner=False,
    )


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health-check: indique si le service est prêt (modèle chargé)."""
    return {"status": "ok", "ready": pattern_adapter is not None}


def build_question(user_request: str, executed_sequence: List[str], available_actions: Dict[str, str]) -> str:
    """Construit le prompt patterns pour proposer une suite optimale.

    IMPORTANT : par choix de conception, on NE FOURNIT PLUS la séquence réellement exécutée
    au modèle, afin d'éviter le biais d'ancrage. Le modèle voit uniquement :
    - la requête utilisateur
    - les règles de menus / transitions
    - le catalogue d'actions disponibles.
    """
    lines: List[str] = []
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

    lines.append("Contraintes de menus et de transitions (IMPORTANT) :")
    lines.append("- Tu démarres TOUJOURS dans le menu de base.")
    lines.append("- Dans le menu de base, tu ne peux utiliser que les codes B1, B2, B3.")
    lines.append("- Si tu choisis B2, tu passes au menu général.")
    lines.append("- Dans le menu général, tu ne peux utiliser que les codes G1, G2, G3, G4, G5, G6.")
    lines.append("- Dans le menu général, la SEULE façon de revenir au menu de base est de choisir G6,")
    lines.append("  puis tu peux de nouveau utiliser uniquement B1, B2, B3.")
    lines.append("- Tu ne dois JAMAIS proposer une transition impossible, par exemple :")
    lines.append("  - utiliser B3 immédiatement après G1 (sans passer par G6 pour revenir au menu de base),")
    lines.append("  - utiliser G1 immédiatement après B3 (car après B3, on ne revient pas dans le menu général).")
    lines.append("- Toutes les suites que tu proposes doivent donc être EXÉCUTABLES dans ce système de menus.")
    lines.append("")

    lines.append("Contexte :")
    lines.append(f'- Requête de l\'utilisateur : "{user_request}"')
    lines.append("")
    lines.append("- Liste d'actions possibles (codes → description) :")
    for code, desc in available_actions.items():
        lines.append(f"  - {code} : {desc}")
    lines.append("")

    # On ne fournit plus la suite réellement exécutée pour éviter le biais de confirmation.
    lines.append("")

    # Conseils de stratégie (non obligatoires) pour aider à choisir la suite optimale
    lines.append("Conseils de stratégie (non obligatoires) :")
    lines.append(
        "- Si la requête concerne qui est LIA ou son identité globale, il est souvent utile d'utiliser G1."
    )
    lines.append(
        "- Si la requête concerne les traits de LIA (sa personnalité, ses façons d'être), il est souvent utile d'utiliser G2."
    )
    lines.append(
        "- Si la requête concerne l'environnement de LIA ou ses capacités (ce qu'elle peut faire), il est souvent utile d'utiliser G3."
    )
    lines.append(
        "- Utilise G4 surtout pour aller chercher des souvenirs ou faits spécifiques déjà mémorisés (événements passés, informations externes)."
    )
    lines.append(
        "- Après avoir collecté les informations nécessaires, termine généralement par une action de réponse (B3 ou G5 selon le menu)."
    )
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
    lines.append("")
    lines.append("Format de réponse EXIGÉ :")
    lines.append("- Une seule ligne de la forme : {B2, G4, G5}")
    lines.append("- Sans introduction, sans explication, sans texte additionnel.")
    lines.append("")
    lines.append("Réponds maintenant avec UNIQUEMENT la suite optimale au format {Xy, Xy, ...}.")

    return "\n".join(lines)


def parse_pattern_sequence(raw: str, allowed_codes: List[str]) -> List[str]:
    """Parse la suite `{Xy, Xy, ...}` renvoyée par le modèle."""
    import re

    if not raw:
        return []

    m = re.search(r"\{([^}]*)\}", raw)
    inside = m.group(1) if m else raw

    candidates = re.findall(r"[A-Z]\d+", inside)
    allowed_set = set(allowed_codes)
    return [c for c in candidates if c in allowed_set]


@app.post("/patterns/recommend", response_model=PatternResponse)
async def recommend_pattern(req: PatternRequest) -> PatternResponse:
    """Recommande une suite de codes pour les menus internes."""
    adapter = pattern_adapter
    if adapter is None:
        # Service pas encore prêt (le modèle GGUF peut être en cours de chargement)
        return PatternResponse(sequence=[], raw="")
    actions = req.actions_catalog or ACTIONS_CATALOG

    question = build_question(
        user_request=req.user_request,
        executed_sequence=req.executed_sequence,
        available_actions=actions,
    )

    raw = await adapter._generate_internal(  # type: ignore[attr-defined]
        message=question,
        context=None,
        session_id="pattern_brain",
        use_classic_prompt=False,
    )

    seq = parse_pattern_sequence(raw, allowed_codes=list(actions.keys()))
    return PatternResponse(sequence=seq, raw=raw or "")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Service Pattern Brain (patterns internes)")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse IP")
    parser.add_argument("--port", type=int, default=8002, help="Port")

    args = parser.parse_args()

    uvicorn.run(
        "support.pattern_brain_service:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


