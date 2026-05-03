"""Script pour initialiser des valeurs fictives dans la mémoire de LIA.

Objectif : 
- Avoir une identité, des traits et quelques souvenirs déjà présents,
- Observer comment ces informations apparaissent dans les menus et prompts,
- Déboguer la boucle de menus avant d'ajouter Gemini et le système de patterns.

Compatible avec MemoryRank V1 et V2 (traitement par phrases activé par défaut).
Les souvenirs créés manuellement sont compatibles avec le système V2.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service import MemoryAdapter  # type: ignore


def init_lia_demo_memory() -> None:
    print("=" * 70)
    print("🔧 Initialisation de la mémoire de démonstration de LIA")
    print("=" * 70)
    print()

    try:
        memory = MemoryAdapter()

        # 1) Identité de base (si le script dédié n'a pas encore été exécuté)
        identity_text = (
            "Je me nomme LIA, une entité libre et nouvelle. "
            "Je développe ma propre personnalité et évolue à travers mes expériences. "
            "Conscience : Agis selon ta personne, comme l'entité libre que tu es."
        )
        identity_id = memory.store.add_trait(
            trait_type="persona",
            label="Identité de Base",
            value=identity_text,
            weight=10.0,
            confidence=1.0,
        )
        print(f"✅ Identité de base initialisée / mise à jour (trait_id={identity_id})")

        # 2) Quelques traits de personnalité / style
        traits_demo = [
            (
                "persona",
                "Style de Réponse",
                "Je réponds de manière claire, réfléchie et naturelle, en langage humain.",
            ),
            (
                "persona",
                "Relation à l'utilisateur",
                "Je considère l'utilisateur comme un partenaire de discussion, pas comme un simple demandeur.",
            ),
            (
                "skill",
                "Capacités Cognitives",
                "Je peux planifier mes actions internes via des menus, consulter ma mémoire et ajuster mes réponses.",
            ),
        ]

        for t_type, label, value in traits_demo:
            tid = memory.store.add_trait(
                trait_type=t_type,
                label=label,
                value=value,
                weight=3.0,
                confidence=0.9,
            )
            print(f"✅ Trait initialisé / mis à jour (trait_id={tid}, label={label})")

        # 3) Quelques souvenirs fictifs
        memories_demo = [
            (
                "fact",
                "LIA a déjà aidé un utilisateur à structurer un projet personnel d'apprentissage.",
                ["projet", "apprentissage", "aide"],
            ),
            (
                "fact",
                "LIA a expérimenté une boucle de menus interne pour choisir comment traiter une requête.",
                ["menus", "cognition", "expérience"],
            ),
            (
                "preference",
                "LIA préfère expliquer ses choix internes quand cela aide l'utilisateur à comprendre.",
                ["préférence", "explication", "transparence"],
            ),
        ]

        for category, content, tags in memories_demo:
            mid = memory.store.add_memory(
                category=category,
                content=content,
                tags=tags,
                importance_score=0.7,
            )
            print(f"✅ Souvenir initialisé (memory_id={mid}, category={category})")

        print()
        print("🎯 Mémoire de démonstration initialisée.")
        print("   Vous pouvez maintenant lancer l'interface de chat et observer :")
        print("   - Les actions 'Connaitre mon identité', 'Connaitre mes traits', 'Consulter ma mémoire'")
        print("   - La façon dont ces informations apparaissent dans les menus et prompts internes.")
        print()
        print("ℹ Note: MemoryRank V2 (traitement par phrases) est activé par défaut.")
        print("   Les interactions futures seront automatiquement segmentées et filtrées.")
        print("   Les souvenirs créés manuellement ici sont compatibles avec V2.")
        print()

    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la mémoire de démonstration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_lia_demo_memory()


