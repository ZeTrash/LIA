"""Tests pour le canal d'échange avec le noyau d'appui."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from support import SupportChannel, SupportConfig, GeminiAdapter, LearningService
from memory_service import MemoryAdapter


async def test_support_channel():
    """Test du canal d'échange avec le noyau d'appui."""
    print("=" * 70)
    print("🧪 Test du Canal Support (Noyau d'Appui)")
    print("=" * 70)
    print()
    
    # Configuration
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    if not config.gemini_api_key or config.gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("⚠️  Clé API Gemini non configurée")
        print("   Le test nécessite Gemini pour fonctionner.")
        return
    
    # Initialiser les services
    print("🔧 Initialisation du canal Support...")
    memory = MemoryAdapter()
    gemini_adapter = GeminiAdapter(config)
    
    # Créer le canal Support
    support_channel = SupportChannel(
        gemini_adapter=gemini_adapter,
        memory_adapter=memory,
        config=config
    )
    
    print("✅ Canal Support initialisé")
    print()
    
    # Test 1: Interrogation simple
    print("=" * 70)
    print("Test 1: Interrogation simple via le canal")
    print("=" * 70)
    print()
    
    question1 = "Qu'est-ce que l'intelligence artificielle en une phrase ?"
    print(f"📡 Question: {question1}")
    print()
    
    try:
        result = await support_channel.query(
        question=question1,
        save_to_memory=True,
        session_id="test_support_channel"
    )
        
        print(f"✅ Réponse reçue (échange {result['exchange_id'][:8]}):")
        print(f"   {result['answer'][:200]}...")
        print()
        
        if result.get('memory_id'):
            print(f"✅ Connaissance sauvegardée dans la mémoire: {result['memory_id']}")
        print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    # Test 2: Exploration d'un sujet
    print("=" * 70)
    print("Test 2: Exploration d'un sujet")
    print("=" * 70)
    print()
    
    topic = "mécanique quantique"
    print(f"🔍 Exploration du sujet: {topic}")
    print()
    
    try:
        exploration_result = await support_channel.explore_topic(
            topic=topic,
            depth=2,
            session_id="test_support_channel"
        )
        
        print(f"✅ Exploration terminée:")
        print(f"   Sujet: {exploration_result['topic']}")
        print(f"   Profondeur: {exploration_result['depth']}")
        print(f"   Connaissances apprises: {exploration_result['count']}")
        print()
        
        for i, learning in enumerate(exploration_result.get('learnings', []), 1):
            print(f"   {i}. {learning.get('question', '')[:60]}...")
            if learning.get('memory_id'):
                print(f"      → Sauvegardé: {learning['memory_id']}")
        print()
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exploration: {e}")
        return
    
    # Test 3: Historique des échanges
    print("=" * 70)
    print("Test 3: Historique des échanges")
    print("=" * 70)
    print()
    
    history = support_channel.get_history()
    print(f"✅ Historique: {len(history)} échange(s) enregistré(s)")
    print()
    
    for i, exchange in enumerate(history[-3:], 1):  # Afficher les 3 derniers
        print(f"   {i}. [{exchange['timestamp'][:19]}] {exchange['question'][:50]}...")
        if exchange.get('memory_id'):
            print(f"      → Mémoire: {exchange['memory_id']}")
    print()
    
    # Test 4: Disponibilité
    print("=" * 70)
    print("Test 4: Vérification de disponibilité")
    print("=" * 70)
    print()
    
    is_available = support_channel.is_available()
    print(f"✅ Canal disponible: {is_available}")
    print()
    
    print("=" * 70)
    print("✅ Tests terminés")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_support_channel())

