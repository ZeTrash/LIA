#!/usr/bin/env python3
"""Exécute les expériences de prompting et enregistre les échanges.

Usage:
  cd /opt/LIA
  python -m prompting_sandbox.run_experiments
  python -m prompting_sandbox.run_experiments --output-dir ./prompting_sandbox/outputs
  python -m prompting_sandbox.run_experiments --conversations conv_01 conv_03  # Limiter aux convs spécifiques
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

# Ajouter la racine du projet au PYTHONPATH
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from core import LLMAdapter, CoreConfig
from prompting_sandbox.canonical_model import CanonicalPromptModel


def load_conversations(conversations_dir: Path, ids_filter: list[str] | None = None) -> list[dict]:
    """Charge les conversations depuis les fichiers JSON."""
    conversations = []
    for f in sorted(conversations_dir.glob("conv_*.json")):
        conv_id = f.stem  # ex: conv_01_identite
        if ids_filter:
            # Match conv_01 contre conv_01_identite
            matched = any(conv_id.startswith(fid) or fid.startswith(conv_id) for fid in ids_filter)
            if not matched:
                continue
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            data["_file"] = str(f)
            conversations.append(data)
    return conversations


def _write_jsonl(fp: TextIO, obj: dict) -> None:
    fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fp.flush()


def _write_transcript_header(fp: TextIO, run_meta: dict) -> None:
    fp.write("# Transcript - Sandbox de Prompting\n\n")
    fp.write("## Meta\n\n")
    fp.write("```json\n")
    fp.write(json.dumps(run_meta, ensure_ascii=False, indent=2))
    fp.write("\n```\n\n")
    fp.flush()


def _write_transcript_turn_start(fp: TextIO, exchange_stub: dict, wrote_conv_headers: set[str]) -> None:
    """Écrit message+prompt immédiatement (avant génération)."""
    conv_id = str(exchange_stub.get("conversation_id", "unknown"))
    if conv_id not in wrote_conv_headers:
        fp.write(f"## {conv_id}\n\n")
        wrote_conv_headers.add(conv_id)

    turn = exchange_stub.get("turn", "?")
    fp.write(f"### Tour {turn}\n\n")

    fp.write("**Message utilisateur**\n\n")
    fp.write(str(exchange_stub.get("user_message", "")) + "\n\n")

    fp.write("**Prompt envoyé**\n\n")
    fp.write("```text\n")
    prompt = str(exchange_stub.get("prompt_sent", ""))
    fp.write(prompt)
    if not prompt.endswith("\n"):
        fp.write("\n")
    fp.write("```\n\n")

    fp.write("**Réponse**\n\n")
    fp.flush()


def _write_transcript_turn_end(fp: TextIO, response: str) -> None:
    """Écrit la réponse (complète) pour terminer le tour."""
    fp.write(response + "\n\n")
    fp.flush()


def _write_transcript_exchange(fp: TextIO, exchange: dict, wrote_conv_headers: set[str]) -> None:
    conv_id = str(exchange.get("conversation_id", "unknown"))
    if conv_id not in wrote_conv_headers:
        fp.write(f"## {conv_id}\n\n")
        wrote_conv_headers.add(conv_id)

    turn = exchange.get("turn", "?")
    fp.write(f"### Tour {turn}\n\n")

    fp.write("**Message utilisateur**\n\n")
    fp.write(str(exchange.get("user_message", "")) + "\n\n")

    fp.write("**Prompt envoyé**\n\n")
    fp.write("```text\n")
    prompt = str(exchange.get("prompt_sent", ""))
    fp.write(prompt)
    if not prompt.endswith("\n"):
        fp.write("\n")
    fp.write("```\n\n")

    fp.write("**Réponse**\n\n")
    fp.write(str(exchange.get("model_response", "")) + "\n\n")
    fp.flush()


async def run_experiments(
    output_dir: Path,
    conversations_dir: Path,
    ids_filter: list[str] | None = None,
    continuous_session: bool = False,
    context_turns: int = 5,
    model_path: Path | None = None,
    prompt_model: str = "schema",
) -> None:
    """Charge le modèle, exécute les conversations et enregistre les échanges."""
    print("=" * 70)
    print("Sandbox de Prompting - Expériences")
    print("=" * 70)

    # Trouver le modèle GGUF (par défaut: privilégier un modèle plus léger pour itérer vite)
    if model_path is not None:
        gguf_path = model_path
    else:
        candidates = [
            _project_root / "models" / "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            _project_root / "models" / "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
            _project_root / "models" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            _project_root / "models" / "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        ]
        gguf_path = next((p for p in candidates if p.exists()), candidates[-1])

    if not gguf_path.exists():
        print(f"\n❌ Aucun modèle GGUF trouvé. Vérifiez models/")
        print("   Cherché (ordre): Qwen 7B, Qwen 3B, Llama 3B, Qwen 1.5B")
        sys.exit(1)

    print(f"\n📦 Chargement du modèle: {gguf_path.name}")
    core_config = CoreConfig(
        use_gguf=True,
        gguf_model_path=str(gguf_path.resolve()),
        max_length=512,
        temperature=0.8,
    )

    adapter = LLMAdapter(
        config=core_config,
        use_memory=False,
        gemini_adapter=None,
        support_channel=None,
        use_cognitive_planner=False,
    )
    print("✅ Modèle chargé\n")

    # Charger le modèle canonique (prompt)
    canonical = CanonicalPromptModel(prompt_model=prompt_model)
    print(f"📋 Modèle de prompt chargé: {prompt_model}\n")

    # Charger les conversations
    conversations = load_conversations(conversations_dir, ids_filter)
    if not conversations:
        print("❌ Aucune conversation trouvée")
        sys.exit(1)

    print(f"📂 {len(conversations)} conversation(s) à exécuter\n")

    # Résultats à enregistrer
    all_exchanges: list[dict] = []
    run_meta = {
        "timestamp": datetime.now().isoformat(),
        "model": gguf_path.name,
        "conversations_count": len(conversations),
        "continuous_session": continuous_session,
        "context_turns": context_turns,
        "prompt_model": prompt_model,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"exchanges_{timestamp_str}.json"
    output_file_jsonl = output_dir / f"exchanges_{timestamp_str}.jsonl"
    output_file_transcript = output_dir / f"transcript_{timestamp_str}.md"

    # Écriture au fil de l'eau: JSONL + transcript (utile si run long / interruption)
    wrote_conv_headers: set[str] = set()
    with (
        open(output_file_jsonl, "w", encoding="utf-8") as fp_jsonl,
        open(output_file_transcript, "w", encoding="utf-8") as fp_md,
    ):
        _write_jsonl(fp_jsonl, {"meta": run_meta})
        _write_transcript_header(fp_md, run_meta)

        # État global si on veut exécuter plusieurs scénarios en conversation continue
        global_recent_interactions: list[tuple[str, str]] = []

        for conv in conversations:
            conv_id = conv.get("id", "unknown")
            title = conv.get("title", conv_id)
            messages = conv.get("messages", [])

            print("-" * 50)
            print(f"📌 {conv_id}: {title}")
            print("-" * 50)

            # État de la conversation (pour multi-tours)
            recent_interactions: list[tuple[str, str]] = (
                global_recent_interactions if continuous_session else []
            )

            for i, user_msg in enumerate(messages):
                print(f"\n  Message {i + 1}/{len(messages)}: {user_msg[:60]}...")

                # Mettre à jour le modèle canonique avec le contexte accumulé
                canonical_with_context = canonical.with_recent_interactions(recent_interactions)
                canonical_with_context.max_recent_interactions = context_turns

                # Construire le prompt
                prompt = canonical_with_context.build_prompt(user_msg, model_name=gguf_path.name)

                # Écrire dès maintenant (même si la génération est longue)
                exchange_stub = {
                    "event": "turn_start",
                    "conversation_id": conv_id,
                    "turn": i + 1,
                    "user_message": user_msg,
                    "prompt_sent": prompt,
                    "prompt_length_chars": len(prompt),
                }
                _write_jsonl(fp_jsonl, exchange_stub)
                _write_transcript_turn_start(fp_md, exchange_stub, wrote_conv_headers)

                # Générer la réponse
                try:
                    response = await adapter.generate_from_raw_prompt(prompt)
                except Exception as e:
                    response = f"[ERREUR: {e}]"
                    print(f"  ⚠️  Erreur: {e}")

                # Enregistrer l'échange
                exchange = {
                    "event": "exchange",
                    "conversation_id": conv_id,
                    "turn": i + 1,
                    "user_message": user_msg,
                    "prompt_sent": prompt,
                    "model_response": response,
                    "prompt_length_chars": len(prompt),
                    "response_length_chars": len(response),
                }
                all_exchanges.append(exchange)

                # Finir le tour dans le transcript + écrire l'échange complet
                _write_transcript_turn_end(fp_md, response)
                _write_jsonl(fp_jsonl, exchange)

                # Accumuler pour le prochain tour
                recent_interactions.append((user_msg, response))

                print(f"  Réponse: {response[:100]}..." if len(response) > 100 else f"  Réponse: {response}")

            print()

            # Si on est en mode continu, persister l'état global
            if continuous_session:
                global_recent_interactions = recent_interactions

    output_data = {
        "meta": run_meta,
        "exchanges": all_exchanges,
    }

    with open(output_file, "w", encoding="utf-8") as fp:
        json.dump(output_data, fp, ensure_ascii=False, indent=2)

    print("=" * 70)
    print(f"✅ Échanges enregistrés: {output_file}")
    print(f"✅ Échanges (JSONL): {output_file_jsonl}")
    print(f"✅ Transcript (Markdown): {output_file_transcript}")
    print(f"   Total: {len(all_exchanges)} échange(s)")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exécute les expériences de prompting")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "outputs",
        help="Dossier de sortie pour les fichiers d'échanges",
    )
    parser.add_argument(
        "--conversations-dir",
        type=Path,
        default=Path(__file__).parent / "conversations",
        help="Dossier contenant les fichiers de conversations JSON",
    )
    parser.add_argument(
        "--conversations",
        nargs="*",
        help="IDs de conversations à exécuter (ex: conv_01 conv_03). Par défaut: toutes.",
    )
    parser.add_argument(
        "--continuous-session",
        action="store_true",
        help="Exécute les conversations sélectionnées comme une seule conversation continue (contexte accumulé).",
    )
    parser.add_argument(
        "--context-turns",
        type=int,
        default=5,
        help="Nombre d'interactions récentes injectées dans le prompt canonique (0 = aucune).",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Chemin vers un modèle GGUF spécifique (sinon: sélection automatique d'un modèle léger).",
    )
    parser.add_argument(
        "--prompt-model",
        choices=["schema", "simple"],
        default="schema",
        help="Modèle de prompt utilisé: 'schema' (canonical_model_schema.json) ou 'simple' (sections texte).",
    )
    args = parser.parse_args()

    ids_filter = None
    if args.conversations:
        # Normaliser les IDs (conv_01 ou conv_01_identite)
        ids_filter = []
        for c in args.conversations:
            if not c.startswith("conv_"):
                c = f"conv_{c}"
            ids_filter.append(c)

    asyncio.run(
        run_experiments(
            output_dir=args.output_dir,
            conversations_dir=args.conversations_dir,
            ids_filter=ids_filter,
            continuous_session=args.continuous_session,
            context_turns=args.context_turns,
            model_path=args.model_path,
            prompt_model=args.prompt_model,
        )
    )


if __name__ == "__main__":
    main()
