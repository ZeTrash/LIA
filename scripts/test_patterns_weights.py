"""Script de test pour le calcul et le stockage des poids de patterns.

But:
- Simuler plusieurs réponses parsées de Gemini (séquences de codes: B2, G1, B3, ...),
- Calculer les poids selon l'ordre (cf. `SYSTEME_PATTERNS.md`),
- Upserter dans la table `patterns`,
- Afficher l'évolution des lignes de la table `patterns`.

Ce script ne touche pas encore au système de menus en production.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from memory_service import MemoryAdapter, PatternModel, get_db  # type: ignore
except ModuleNotFoundError as e:
    # Cas typique: exécution via /bin/python3 au lieu de /opt/LIA/venv/bin/python
    if e.name == "sqlalchemy":
        raise SystemExit(
            "Dépendance manquante: sqlalchemy.\n"
            "Tu exécutes probablement le script avec le mauvais Python (ex: /bin/python3).\n\n"
            "Utilise plutôt:\n"
            "  source /opt/LIA/venv/bin/activate\n"
            "  python3 scripts/test_patterns_weights.py\n\n"
            f"Python courant: {sys.executable}\n"
        )
    raise


def compute_order_weights(sequence: List[str]) -> Dict[str, float]:
    """Calcule les poids d'une séquence selon l'ordre.

    Formule (doc): poids(action_i) = (n - i + 1) / somme(1..n), i commençant à 1.
    Si un même code apparaît plusieurs fois, on additionne ses contributions.
    """
    n = len(sequence)
    if n == 0:
        return {}
    denom = n * (n + 1) / 2.0  # somme(1..n)
    weights: Dict[str, float] = {}
    for idx, code in enumerate(sequence, start=1):
        contrib = (n - idx + 1) / denom
        weights[code] = weights.get(code, 0.0) + contrib

    # Normalisation de sécurité
    total = sum(weights.values())
    if total > 0:
        for k in list(weights.keys()):
            weights[k] = weights[k] / total
    return weights


def print_patterns_table() -> None:
    """Affiche l'état courant de la table `patterns`."""
    db = get_db()
    session = db.get_session()
    try:
        rows = session.query(PatternModel).order_by(
            PatternModel.menu_context, PatternModel.prev_step
        ).all()
        print("\n=== État actuel de la table patterns ===")
        if not rows:
            print("(vide)")
            return
        for p in rows:
            print(
                f"- id={p.pattern_id} | ctx={p.menu_context} | prev={p.prev_step} | "
                f"rec={p.recommended_step} | source={p.source} | conf={p.confidence:.2f}"
            )
            print(f"  weights={p.weights}")
        print("========================================\n")
    finally:
        session.close()


def reset_pattern_row(menu_context: str, prev_step: str) -> int:
    """Supprime la ligne (menu_context, prev_step) si elle existe. Retourne nb lignes supprimées."""
    db = get_db()
    session = db.get_session()
    try:
        deleted = (
            session.query(PatternModel)
            .filter(PatternModel.menu_context == menu_context, PatternModel.prev_step == prev_step)
            .delete()
        )
        session.commit()
        return int(deleted or 0)
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Supprime d'abord la ligne (menu_context='base', prev_step='initial') pour partir d'un état propre.",
    )
    args = parser.parse_args()

    print(f"Python utilisé: {sys.executable}")
    memory = MemoryAdapter()

    # Cas de test : on rejoue les séquences obtenues avec Gemini (logs @bash 62-240)
    test_cases = [
        # (menu_context, prev_step, sequence)
        ("base", "initial", ["B3"]),  # Bonjour → répondre direct
        ("base", "initial", ["B2", "G1", "B3"]),  # Qui es-tu ?
        ("base", "initial", ["B2", "G3", "G5"]),  # Que peux-tu faire dans ton environnement ?
    ]

    print("=== Simulation de poids de patterns ===")
    if args.reset:
        deleted = reset_pattern_row("base", "initial")
        print(f"Reset demandé: suppression de {deleted} ligne(s) pour (ctx='base', prev='initial').")
        print_patterns_table()

    for idx, (ctx, prev, seq) in enumerate(test_cases, start=1):
        print(f"\n--- Cas {idx} ---")
        print(f"Contexte menu   : {ctx!r}")
        print(f"Étape précédente: {prev!r}")
        print(f"Séquence Gemini : {seq}")

        weights = compute_order_weights(seq)
        print(f"Poids calculés  : {weights}")

        # On choisit comme étape recommandée le premier code de la séquence
        recommended = seq[0]
        pid = memory.upsert_pattern(
            menu_context=ctx,
            prev_step=prev,
            recommended_step=recommended,
            weights=weights,
            source="gemini_test",
            confidence=0.9,
        )
        print(f"➡ upsert_pattern → pattern_id={pid}")

        # Afficher la table après chaque upsert pour voir l'évolution
        print_patterns_table()


if __name__ == "__main__":
    main()


