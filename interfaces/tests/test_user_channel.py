"""Tests pour le canal utilisateur."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from interfaces import UserChannel
from core import CoreConfig
from support import SupportChannel, SupportConfig, GeminiAdapter
from memory_service import MemoryAdapter


async def test_user_channel():
    """Test du canal utilisateur."""
    print("=" * 70)
    print("🧪 Test du Canal Utilisateur")
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
    
    # Initialiser les services
    print("🔧 Initialisation du canal utilisateur...")
    memory = MemoryAdapter()
    
    # Optionnel : créer le canal Support pour l'autonomie
    support_channel = None
    try:
        support_config = SupportConfig()
        support_config.load_from_file("config/api.conf")
        if support_config.gemini_api_key and support_config.gemini_api_key != "YOUR_GEMINI_API_KEY_HERE":
            gemini_adapter = GeminiAdapter(support_config)
            support_channel = SupportChannel(
                gemini_adapter=gemini_adapter,
                memory_adapter=memory,
                config=support_config
            )
            print("✅ Canal Support créé (autonomie activée)")
    except Exception as e:
        print(f"⚠️  Canal Support non disponible: {e}")
        print("   Le canal utilisateur fonctionnera sans autonomie")
    
    # Créer le canal utilisateur
    user_channel = UserChannel(
        memory_adapter=memory,
        support_channel=support_channel,
        core_config=core_config
    )
    
    print("✅ Canal utilisateur initialisé")
    print()
    
    # Test 1: Interaction simple
    print("=" * 70)
    print("Test 1: Interaction simple")
    print("=" * 70)
    print()
    
    session_id = "test_session_1"
    message1 = "Bonjour LIA, comment vas-tu ?"
    
    print(f"👤 Utilisateur: {message1}")
    print()
    
    try:
        result1 = await user_channel.send_message(
            message=message1,
            session_id=session_id,
            use_autonomy=True
        )
        
        print(f"🤖 LIA: {result1['lia_response'][:200]}...")
        print()
        print(f"✅ Interaction enregistrée (ID: {result1['interaction_id'][:8]})")
        print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Question nécessitant des connaissances
    print("=" * 70)
    print("Test 2: Question nécessitant des connaissances")
    print("=" * 70)
    print()
    
    message2 = "Qu'est-ce que l'intelligence artificielle ?"
    
    print(f"👤 Utilisateur: {message2}")
    print()
    
    try:
        result2 = await user_channel.send_message(
            message=message2,
            session_id=session_id,
            use_autonomy=True
        )
        
        print(f"🤖 LIA: {result2['lia_response'][:300]}...")
        print()
        print(f"✅ Interaction enregistrée (ID: {result2['interaction_id'][:8]})")
        print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Historique de session
    print("=" * 70)
    print("Test 3: Historique de session")
    print("=" * 70)
    print()
    
    session_history = user_channel.get_session_history(session_id)
    print(f"✅ Historique de la session '{session_id}': {len(session_history)} interaction(s)")
    print()
    
    for i, interaction in enumerate(session_history, 1):
        status = "✅" if interaction.get('success') else "❌"
        print(f"   {i}. {status} [{interaction['timestamp'][:19]}]")
        print(f"      Utilisateur: {interaction['user_message'][:60]}...")
        if interaction.get('lia_response'):
            print(f"      LIA: {interaction['lia_response'][:60]}...")
        if interaction.get('error'):
            print(f"      Erreur: {interaction['error'][:60]}...")
    print()
    
    # Test 4: Statistiques
    print("=" * 70)
    print("Test 4: Statistiques")
    print("=" * 70)
    print()
    
    stats = user_channel.get_statistics()
    print(f"✅ Statistiques du canal utilisateur:")
    print(f"   Total interactions: {stats['total_interactions']}")
    print(f"   Réussies: {stats['successful']}")
    print(f"   Échouées: {stats['failed']}")
    print(f"   Taux de réussite: {stats['success_rate']:.1%}")
    print(f"   Sessions uniques: {stats['unique_sessions']}")
    print()
    
    # Test 5: Nouvelle session
    print("=" * 70)
    print("Test 5: Nouvelle session")
    print("=" * 70)
    print()
    
    session_id_2 = "test_session_2"
    message3 = "Qui es-tu ?"
    
    print(f"👤 Utilisateur (session {session_id_2[:8]}): {message3}")
    print()
    
    try:
        result3 = await user_channel.send_message(
            message=message3,
            session_id=session_id_2,
            use_autonomy=True
        )
        
        print(f"🤖 LIA: {result3['lia_response'][:200]}...")
        print()
        
        # Vérifier que les deux sessions sont séparées
        history_1 = user_channel.get_session_history(session_id)
        history_2 = user_channel.get_session_history(session_id_2)
        
        print(f"✅ Session 1: {len(history_1)} interaction(s)")
        print(f"✅ Session 2: {len(history_2)} interaction(s)")
        print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 70)
    print("✅ Tests terminés")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_user_channel())

