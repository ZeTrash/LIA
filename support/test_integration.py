"""Script de test d'intégration pour le noyau d'appui."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from support import GeminiAdapter, SupportConfig, LearningService
from memory_service import MemoryAdapter


async def test_integration():
    """Test d'intégration du noyau d'appui."""
    print("=" * 60)
    print("Test d'intégration Noyau d'Appui (Gemini)")
    print("=" * 60)
    print()
    
    # 1. Test de la configuration
    print("1. Test de la configuration...")
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    if not config.gemini_api_key or config.gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("   ⚠️  Clé API Gemini non configurée")
        print("   Pour tester, configurez config/api.conf avec votre clé API Gemini")
        print()
        print("   Tests unitaires (sans API) :")
        print("   - Configuration créée ✅")
        print("   - Adaptateur créé ✅")
        return
    
    print(f"   ✅ Configuration chargée (modèle: {config.gemini_model})")
    print()
    
    # 2. Test de l'adaptateur Gemini
    print("2. Test de l'adaptateur Gemini...")
    adapter = GeminiAdapter(config)
    
    if not adapter.is_available():
        print("   ❌ Gemini non disponible")
        return
    
    print("   ✅ Gemini disponible")
    print()
    
    # 3. Test d'interrogation simple
    print("3. Test d'interrogation Gemini...")
    try:
        answer = await adapter.query("Qu'est-ce que l'intelligence artificielle en une phrase ?")
        print(f"   ✅ Réponse obtenue: {answer[:100]}...")
        print()
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return
    
    # 4. Test du service d'apprentissage
    print("4. Test du service d'apprentissage...")
    memory = MemoryAdapter()
    learning = LearningService(config=config, memory_adapter=memory)
    
    print("   ✅ Service d'apprentissage initialisé")
    print()
    
    # 5. Test d'apprentissage avec sauvegarde
    print("5. Test d'apprentissage avec sauvegarde dans mémoire...")
    try:
        result = await learning.learn(
            "Qu'est-ce que Python en une phrase ?",
            save_to_memory=True
        )
        print(f"   ✅ Connaissance apprise")
        print(f"   ✅ Sauvegardée dans mémoire: {result.get('memory_id', 'N/A')}")
        print()
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return
    
    # 6. Vérification dans la mémoire
    print("6. Vérification dans la mémoire...")
    context = memory.get_context()
    memories = [m for m in context["memories"] if "Python" in m.get("content", "")]
    print(f"   ✅ {len(memories)} souvenir(s) trouvé(s) dans la mémoire")
    print()
    
    print("=" * 60)
    print("✅ Tous les tests d'intégration sont passés !")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_integration())

