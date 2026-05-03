"""Script de test pour le système de patterns avec Gemini.

Objectif (Phase doc `SYSTEME_PATTERNS.md` §1.2, lignes 127–128) :
- Préparer une requête à envoyer à Gemini avec :
  - la requête utilisateur
  - la liste des actions possibles (B1, B2, G1, G2, G3, G4, G5, G6)
  - la suite d'actions réellement choisie par LIA
- Recevoir la réponse de Gemini et la parser au format `{Xy, Xy, ...}`.

Ce script NE BRANCHE PAS ENCORE les résultats dans le système :
- il affiche simplement :
  - le prompt envoyé
  - la réponse brute de Gemini
  - la suite parsée (liste de codes)
  - les éventuelles erreurs de format
"""

import asyncio
import sys
from pathlib import Path
import re
from typing import List, Dict, Any, Optional

# Assurer le PYTHONPATH correct quand on lance depuis /opt/LIA
sys.path.insert(0, str(Path(__file__).parent.parent))

from support import SupportConfig, GeminiAdapter  # type: ignore
from core import LLMAdapter, CoreConfig  # type: ignore


ACTIONS_CATALOG: Dict[str, str] = {
    # Base menu
    "B1": "Voir la demande de l'utilisateur.",
    "B2": "Consulter ma mémoire et me connaitre (menu général).",
    "B3": "Répondre à la requête de l'utilisateur.",
    # General menu
    "G1": "Connaitre mon identité.",
    "G2": "Connaitre mes traits.",
    "G3": "Connaitre mon environnement / mes capacités.",
    "G4": "Consulter ma mémoire.",
    "G5": "Répondre à la requête de l'utilisateur.",
    "G6": "Revenir au menu précédent.",
}


def build_gemini_question(
    user_request: str,
    executed_sequence: List[str],
    available_actions: Dict[str, str],
) -> str:
    """Construit le prompt à envoyer à Gemini pour recommander une suite optimale."""

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

    lines.append("Contexte :")
    lines.append(f'- Requête de l\'utilisateur : "{user_request}"')
    lines.append("")
    lines.append("- Liste d'actions possibles (codes → description) :")
    for code, desc in available_actions.items():
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
    """Parse la suite `{Xy, Xy, ...}` renvoyée par Gemini."""
    if not raw:
        return []

    # Chercher la première paire d'accolades
    m = re.search(r"\{([^}]*)\}", raw)
    inside = m.group(1) if m else raw

    # Extraire tous les codes Xy (B1, G4, etc.)
    candidates = re.findall(r"[A-Z]\d+", inside)
    # Ne garder que ceux qui sont dans la liste autorisée
    allowed_set = set(allowed_codes)
    return [c for c in candidates if c in allowed_set]


_AGENT_ADAPTER: Optional[LLMAdapter] = None


async def get_agent_adapter() -> LLMAdapter:
    """Initialise (une seule fois) un LLMAdapter pour tester le même prompt côté agent."""
    global _AGENT_ADAPTER
    if _AGENT_ADAPTER is not None:
        return _AGENT_ADAPTER

    project_root = Path(__file__).parent.parent
    # Préférer Qwen2.5-7B si disponible, sinon fallback.
    qwen_path = project_root / "models" / "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
    llama_path = project_root / "models" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    gguf_path = qwen_path if qwen_path.exists() else llama_path

    if gguf_path.exists():
        core_config = CoreConfig(
            use_gguf=True,
            gguf_model_path=str(gguf_path.resolve()),
            max_length=64,
            temperature=0.1,
            top_p=0.9,
            top_k=5,
        )
    else:
        # Fallback: modèle par défaut (transformers) si GGUF absent
        core_config = CoreConfig(
            max_length=64,
            temperature=0.1,
            top_p=0.9,
            top_k=5,
        )

    # Pas de mémoire ni planner ici: on veut juste voir comment le modèle brut réagit au prompt
    _AGENT_ADAPTER = LLMAdapter(
        config=core_config,
        use_memory=False,
        gemini_adapter=None,
        support_channel=None,
        use_cognitive_planner=False,
    )
    return _AGENT_ADAPTER


async def ask_agent_pattern(question: str) -> Dict[str, Any]:
    """Envoie le même prompt à l'agent local et parse sa réponse."""
    adapter = await get_agent_adapter()
    print("=== Prompt envoyé à l'AGENT (modèle local) ===")
    print(question)
    print("==============================================\n")

    # Utiliser un prompt simple (pas de sections IDENTITÉ/ENVIRONNEMENT ajoutées automatiquement)
    raw = await adapter._generate_internal(  # type: ignore[attr-defined]
        message=question,
        context=None,
        session_id="patterns_test",
        use_classic_prompt=False,
    )

    print("--- Réponse brute AGENT ---")
    print(raw)
    print("---------------------------\n")

    parsed = parse_pattern_sequence(raw, allowed_codes=list(ACTIONS_CATALOG.keys()))
    print(f"Suite parsée (AGENT)  : {parsed}\n")

    return {"raw": raw, "parsed": parsed}


async def main() -> None:
    # Lecture simple des paramètres
    if len(sys.argv) >= 2:
        user_request = sys.argv[1]
    else:
        user_request = input("Requête utilisateur à analyser (ex: 'Bonjour') : ").strip()

    if not user_request:
        print("❌ Requête utilisateur vide, arrêt.")
        return

    # Suite d'actions exécutée (pour le test, on peut saisir ou utiliser un exemple)
    if len(sys.argv) >= 3:
        seq_arg = sys.argv[2]
        executed_sequence = [s.strip() for s in seq_arg.split(",") if s.strip()]
    else:
        example = "B2, G4, G5"
        seq_input = input(
            f"Suite d'actions exécutée (codes, ex: '{example}') [Entrée pour exemple] : "
        ).strip()
        if not seq_input:
            executed_sequence = [s.strip() for s in example.split(",")]
        else:
            executed_sequence = [s.strip() for s in seq_input.split(",") if s.strip()]

    print("\n=== Paramètres de test ===")
    print(f"- Requête utilisateur : {user_request!r}")
    print(f"- Suite exécutée      : {executed_sequence}")
    print()
    
    # Construire adapter Gemini
    config = SupportConfig()
    adapter = GeminiAdapter(config)

    if not adapter.is_available():
        print("❌ GeminiAdapter non disponible (clé API manquante ou invalide).")
        print("   Configure `config/api.conf` ou la variable d'environnement GEMINI_API_KEY.")
        return

    question = build_gemini_question(
        user_request=user_request,
        executed_sequence=executed_sequence,
        available_actions=ACTIONS_CATALOG,
    )
    
    # 1) Tester le même prompt côté AGENT (modèle local)
    try:
        agent_result = await ask_agent_pattern(question)
        agent_parsed = agent_result.get("parsed", [])
    except Exception as e:
        print(f"⚠️ Erreur lors de l'appel à l'agent local: {e}")
        agent_parsed = []

    print("=== Prompt envoyé à Gemini ===")
    print(question)
    print("==============================\n")

    # Envoyer la requête et parser la réponse, avec quelques tentatives si format mauvais
    max_retries = 3
    attempt = 0
    parsed: List[str] = []
    last_raw = ""

    while attempt < max_retries and not parsed:
        attempt += 1
        print(f"🔎 Appel Gemini (tentative {attempt}/{max_retries})...")
        try:
            answer = await adapter.query(question)
        except Exception as e:
            print(f"❌ Erreur lors de l'appel à Gemini: {e}")
            return

        last_raw = answer or ""
        print("\n--- Réponse brute Gemini ---")
        print(last_raw)
        print("----------------------------\n")

        parsed = parse_pattern_sequence(last_raw, allowed_codes=list(ACTIONS_CATALOG.keys()))
        print(f"Suite parsée : {parsed}")

        if parsed:
            break

        # Si pas de parse valide, renforcer l'instruction dans le prompt pour la prochaine tentative
        question = (
            question
            + "\n\n⚠️ La réponse précédente ne respectait pas le format."
            + " Réponds maintenant UNIQUEMENT par une suite de codes au format {Xy, Xy, ...},"
            + " sans aucun autre texte."
        )

    print("\n=== Résultat final ===")
    print(f"- Suite AGENT (parsée)  : {agent_parsed}")
    if parsed:
        print(f"- Suite GEMINI (parsée) : {parsed}")
    else:
        print("- Suite GEMINI (parsée) : (aucune, format invalide)")
        print("  Dernière réponse brute de Gemini :")
        print(last_raw)


if __name__ == "__main__":
    asyncio.run(main())


