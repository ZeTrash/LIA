"""Test du système de fallback dynamique des modèles Gemini."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from support import GeminiAdapter, SupportConfig


async def test_fallback():
    """Test du système de fallback entre les modèles Gemini."""
    print("=" * 70)
    print("Test du Système de Fallback Dynamique Gemini")
    print("=" * 70)
    print()
    
    # Charger la configuration
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    if not config.gemini_api_key:
        print("❌ Clé API Gemini non configurée dans config/api.conf")
        return
    
    print(f"✅ Clé API chargée: {config.gemini_api_key[:10]}...")
    print()
    
    # Créer l'adaptateur
    adapter = GeminiAdapter(config)
    
    print("📋 Ordre de fallback configuré:")
    for i, model in enumerate(adapter.model_fallback_list, 1):
        print(f"   {i}. {model}")
    print()
    
    # Test 1 : Requête normale (devrait utiliser gemini-2.5-flash)
    print("=" * 70)
    print("Test 1 : Requête normale")
    print("=" * 70)
    print()
    
    try:
        answer = await adapter.query("Qu'est-ce que Python en une phrase ?")
        print(f"✅ Réponse obtenue:")
        print(f"   {answer[:200]}...")
        print()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
    
    # Test 2 : Simuler un échec en utilisant un modèle invalide temporairement
    print("=" * 70)
    print("Test 2 : Simulation de fallback")
    print("=" * 70)
    print()
    
    # Sauvegarder la liste originale
    original_list = adapter.model_fallback_list.copy()
    
    # Modifier temporairement pour simuler un échec du premier modèle
    adapter.model_fallback_list = ["model-inexistant", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
    
    print("⚠️  Premier modèle configuré comme 'model-inexistant' (va échouer)")
    print("   Le système devrait automatiquement passer au suivant...")
    print()
    
    try:
        answer = await adapter.query("Qu'est-ce que JavaScript en une phrase ?")
        print(f"✅ Réponse obtenue (fallback réussi):")
        print(f"   {answer[:200]}...")
        print()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
    finally:
        # Restaurer la liste originale
        adapter.model_fallback_list = original_list
    
    print("=" * 70)
    print("✅ Test terminé")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_fallback())

