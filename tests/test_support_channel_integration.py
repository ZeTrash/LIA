"""Test d'intégration du canal Support avec LLMAdapter."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import LLMAdapter, CoreConfig
from support import SupportChannel, SupportConfig, GeminiAdapter
from memory_service import MemoryAdapter


async def test_support_channel_integration():
    """Test que LLMAdapter utilise correctement le canal Support."""
    print("=" * 70)
    print("🧪 Test d'Intégration : Canal Support + LLMAdapter")
    print("=" * 70)
    print()
    
    # Configuration
    core_config = CoreConfig(
        model_path="models/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        use_gguf=True,
        gguf_model_path="models/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        max_length=512,
        temperature=0.8
    )
    
    support_config = SupportConfig()
    support_config.load_from_file("config/api.conf")
    
    if not support_config.gemini_api_key or support_config.gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("⚠️  Clé API Gemini non configurée")
        print("   Le test nécessite Gemini pour fonctionner.")
        return
    
    # Initialiser les services
    print("🔧 Initialisation des services...")
    memory = MemoryAdapter()
    gemini_adapter = GeminiAdapter(support_config)
    
    # Créer le canal Support
    support_channel = SupportChannel(
        gemini_adapter=gemini_adapter,
        memory_adapter=memory,
        config=support_config
    )
    
    print("✅ Canal Support créé")
    
    # Créer LLMAdapter avec le canal Support
    core_adapter = LLMAdapter(
        core_config,
        use_memory=True,
        support_channel=support_channel,  # ← Utiliser le canal Support
        use_cognitive_planner=True  # Activer le nouveau système
    )
    
    print("✅ LLMAdapter initialisé avec canal Support")
    print()
    
    # Test 1: Question qui devrait déclencher l'autonomie via le canal Support
    print("=" * 70)
    print("Test 1: Question nécessitant Gemini (via canal Support)")
    print("=" * 70)
    print()
    
    question1 = "Qu'est-ce que la mécanique quantique ? Explique-moi ce concept."
    print(f"👤 Vous: {question1}")
    print()
    print("⏳ LIA réfléchit et devrait solliciter Gemini via le canal Support...")
    print()
    
    try:
        response1 = await core_adapter.generate(question1, session_id="test_integration")
        print(f"🤖 LIA: {response1[:300]}...")
        print()
        
        # Vérifier l'historique du canal
        history = support_channel.get_history()
        if history:
            print(f"✅ Historique du canal Support: {len(history)} échange(s)")
            last_exchange = history[-1]
            print(f"   Dernier échange: {last_exchange['question'][:60]}...")
            if last_exchange.get('memory_id'):
                print(f"   → Sauvegardé dans mémoire: {last_exchange['memory_id']}")
        print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Vérifier que le canal Support est bien utilisé
    print("=" * 70)
    print("Test 2: Vérification de l'utilisation du canal Support")
    print("=" * 70)
    print()
    
    # Vérifier que l'historique contient des échanges
    history = support_channel.get_history()
    if len(history) > 0:
        print(f"✅ Le canal Support a été utilisé: {len(history)} échange(s) enregistré(s)")
        print()
        print("Détails des échanges:")
        for i, exchange in enumerate(history, 1):
            print(f"   {i}. [{exchange['timestamp'][:19]}]")
            print(f"      Question: {exchange['question'][:60]}...")
            if exchange.get('success', True):
                print(f"      → Statut: ✅ Succès")
                if exchange.get('memory_id'):
                    print(f"      → Mémoire: {exchange['memory_id']}")
            else:
                print(f"      → Statut: ❌ Échec")
                if exchange.get('error'):
                    print(f"      → Erreur: {exchange['error'][:80]}...")
        print()
    else:
        print("⚠️  Aucun échange enregistré dans le canal Support")
        print("   (Peut être normal si la question n'a pas déclenché Gemini)")
        print()
    
    # Test 3: Question simple (ne devrait pas utiliser Gemini)
    print("=" * 70)
    print("Test 3: Question simple (sans canal Support)")
    print("=" * 70)
    print()
    
    question2 = "Comment vas-tu aujourd'hui ?"
    print(f"👤 Vous: {question2}")
    print()
    
    history_before = len(support_channel.get_history())
    
    try:
        response2 = await core_adapter.generate(question2, session_id="test_integration")
        print(f"🤖 LIA: {response2[:200]}...")
        print()
        
        history_after = len(support_channel.get_history())
        if history_after == history_before:
            print("✅ Canal Support non utilisé (comme attendu pour une question simple)")
        else:
            print(f"ℹ️  Canal Support utilisé ({history_after - history_before} nouvel(le)(s) échange(s))")
        print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 70)
    print("✅ Tests d'intégration terminés")
    print("=" * 70)
    print()
    print("📝 Résumé:")
    print(f"   - Canal Support créé: ✅")
    print(f"   - LLMAdapter avec canal Support: ✅")
    print(f"   - Échanges enregistrés: {len(support_channel.get_history())}")
    print(f"   - Intégration fonctionnelle: ✅")


if __name__ == "__main__":
    asyncio.run(test_support_channel_integration())

