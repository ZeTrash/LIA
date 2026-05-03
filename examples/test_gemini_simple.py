"""Exemple simple pour tester Gemini API."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from support import GeminiAdapter, SupportConfig


async def test_gemini_simple():
    """Test simple de Gemini API."""
    print("=" * 60)
    print("Test Simple Gemini API")
    print("=" * 60)
    print()
    
    # Charger la configuration
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    if not config.gemini_api_key or config.gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("❌ Clé API Gemini non configurée dans config/api.conf")
        print("   Éditez config/api.conf et ajoutez votre clé API")
        return
    
    print(f"✅ Clé API chargée: {config.gemini_api_key[:10]}...")
    print(f"✅ Modèle: {config.gemini_model}")
    print()
    
    # Créer l'adaptateur
    adapter = GeminiAdapter(config)
    
    if not adapter.is_available():
        print("❌ Gemini non disponible")
        return
    
    print("✅ Gemini disponible")
    print()
    
    # Tester avec une question simple
    print("Question: Qu'est-ce que Python en une phrase ?")
    print()
    
    try:
        answer = await adapter.query("Qu'est-ce que Python en une phrase ?")
        print(f"✅ Réponse Gemini:")
        print(f"   {answer}")
        print()
        print("=" * 60)
        print("✅ Test réussi !")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        print("Vérifiez:")
        print("1. La clé API est valide")
        print("2. Le modèle existe (essayez 'gemini-pro' ou 'gemini-1.5-flash')")
        print("3. L'API Gemini est activée dans votre compte Google")


if __name__ == "__main__":
    asyncio.run(test_gemini_simple())

