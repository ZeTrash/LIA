"""Seed de patterns fictifs dans la mémoire (table patterns).

Objectif:
- Tester rapidement l'inclusion d'une recommandation dans les menus
  (avant d'implémenter Gemini et le calcul de poids réel).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service import MemoryAdapter  # type: ignore


def init_fake_patterns() -> None:
    print("=" * 70)
    print("🔧 Seed de patterns fictifs (table patterns)")
    print("=" * 70)
    print()

    memory = MemoryAdapter()

    # Convention de départ (alignée sur les menus actuels) :
    # - menu_context: "base" ou "general"
    # - prev_step: "initial" ou un code d'action (ex: "B2", "G1")
    # - recommended_step: code d'action recommandé
    #
    # Codes (version minimale):
    # Base:
    #   B1 = consult_request
    #   B2 = navigate_general
    #   B3 = respond
    # General:
    #   G1 = consult_identity
    #   G2 = consult_traits
    #   G3 = consult_environment
    #   G4 = consult_memory
    #   G5 = respond
    #   G6 = navigate_base

    seeds = [
        # Premier menu (base) → aller au menu général
        ("base", "initial", "B2", {"B2": 1.0}),
        # Dans le menu général, au début → consulter la mémoire d'abord
        ("general", "initial", "G4", {"G4": 1.0}),
        # Après mémoire (G4) → répondre (G5)
        ("general", "G4", "G5", {"G5": 1.0}),
        # Après identité (G1) → répondre (G5)
        ("general", "G1", "G5", {"G5": 1.0}),
    ]

    for ctx, prev, rec, weights in seeds:
        pid = memory.upsert_pattern(
            menu_context=ctx,
            prev_step=prev,
            recommended_step=rec,
            weights=weights,
            source="seed",
            confidence=0.8,
        )
        print(f"✅ Pattern seed: ctx={ctx}, prev={prev}, rec={rec}, id={pid}")

    print()
    print("🎯 Patterns fictifs seedés.")
    print("   Lance l'interface web et regarde dans le prompt du menu une section RECOMMANDATION.")
    print()


if __name__ == "__main__":
    init_fake_patterns()


