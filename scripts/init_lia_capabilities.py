"""Script pour initialiser les capacités de LIA dans sa mémoire.

Ce script initialise les capacités de LIA comme trait dans la mémoire.
Compatible avec MemoryRank V1 et V2 (traitement par phrases activé par défaut).
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service import MemoryAdapter

def init_lia_capabilities():
    """Initialise le trait des capacités de LIA."""
    print("=" * 70)
    print("🔧 Initialisation des capacités de LIA")
    print("=" * 70)
    print()
    
    try:
        memory = MemoryAdapter()
        
        # Texte des capacités (version condensée pour économiser des tokens)
        # IMPORTANT: éviter la numérotation et le style "document" (réduit la régurgitation de structure)
        # Note: MemoryRank V2 segmentera automatiquement ce texte en phrases lors des interactions
        capabilities_text = (
            "Je suis LIA. Capacités disponibles :\n"
            "- Mémoire : je peux stocker et retrouver souvenirs/traits/objectif.\n"
            "- Groq et Gemini : je peux solliciter une source externe d'information.\n"
            "- Interaction : je peux demander des clarifications à l'utilisateur.\n"
            "- Autonomie : je peux décider quand utiliser ces ressources.\n"
            "- MemoryRank V2 : traitement automatique par phrases des interactions.\n"
        )
        
        # Créer ou mettre à jour le trait
        trait_id = memory.store.add_trait(
            trait_type="skill",
            label="Mes Capacités",
            value=capabilities_text,
            weight=5.0,  # Poids élevé pour ce trait important
            confidence=1.0  # Confiance maximale
        )
        
        print(f"✅ Capacités de LIA initialisées dans la mémoire")
        print(f"   Trait ID: {trait_id}")
        print(f"   Label: Mes Capacités")
        print(f"   Type: skill")
        print(f"   Poids: 5.0")
        print()
        print("Les capacités seront maintenant disponibles dans le contexte de LIA.")
        print()
        print("ℹ Note: MemoryRank V2 (traitement par phrases) est activé par défaut.")
        print("   Les interactions futures seront automatiquement segmentées et filtrées.")
        print()
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_lia_capabilities()

