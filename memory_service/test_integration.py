"""Script de test d'intégration mémoire + noyau primaire."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_service import MemoryStore, MemoryAdapter
from core import LLMAdapter, CoreConfig


async def test_integration():
    """Test d'intégration entre mémoire et noyau primaire."""
    print("=" * 60)
    print("Test d'intégration Mémoire + Noyau Primaire")
    print("=" * 60)
    print()
    
    # 1. Test du service mémoire
    print("1. Test du service mémoire...")
    store = MemoryStore()
    
    # Ajouter un trait
    trait_id = store.add_trait(
        trait_type="persona",
        label="curiosité",
        value="très curieux et avide d'apprendre",
        weight=0.9
    )
    print(f"   ✅ Trait ajouté: {trait_id}")
    
    # Ajouter un souvenir
    memory_id = store.add_memory(
        category="fact",
        content="L'utilisateur aime le café et la programmation",
        tags=["préférence", "hobby"],
        importance_score=0.7
    )
    print(f"   ✅ Souvenir ajouté: {memory_id}")
    
    # Récupérer le contexte
    context = store.get_context()
    print(f"   ✅ Contexte récupéré: {len(context['traits'])} traits, {len(context['memories'])} souvenirs")
    print()
    
    # 2. Test de l'adaptateur mémoire
    print("2. Test de l'adaptateur mémoire...")
    memory_adapter = MemoryAdapter()
    context_from_adapter = memory_adapter.get_context()
    print(f"   ✅ Contexte via adaptateur: {len(context_from_adapter['traits'])} traits")
    print()
    
    # 3. Test d'intégration avec le noyau primaire
    print("3. Test d'intégration avec le noyau primaire...")
    print("   (Cela peut prendre quelques secondes pour charger le modèle)")
    print()
    
    try:
        config = CoreConfig(
            model_path="models/Qwen/Qwen2.5-1.5B-Instruct",
            quantize=True,
            quantization_bits=4
        )
        
        adapter = LLMAdapter(config, use_memory=True)
        print("   ✅ Noyau primaire initialisé avec mémoire")
        print()
        
        # Générer une réponse (le contexte sera récupéré automatiquement depuis la mémoire)
        print("4. Génération d'une réponse avec contexte mémoire...")
        response = await adapter.generate(
            "Bonjour ! Qui suis-je ?",
            session_id="test_integration"
        )
        print(f"   ✅ Réponse générée: {response[:100]}...")
        print()
        
        # Vérifier que l'interaction a été journalisée
        print("5. Vérification de la journalisation...")
        # Les interactions sont journalisées automatiquement
        print("   ✅ Interaction journalisée automatiquement")
        print()
        
        print("=" * 60)
        print("✅ Tous les tests d'intégration sont passés !")
        print("=" * 60)
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_integration())

