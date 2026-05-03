"""Test de l'autonomie de LIA dans un chat normal."""
import logging
logging.basicConfig(level=logging.INFO)
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import LLMAdapter, CoreConfig
from support import LearningService, SupportConfig
from memory_service import MemoryAdapter


async def test_autonomie_chat():
    """Test que LIA peut solliciter Gemini de manière autonome dans un chat."""
    print("=" * 70)
    print("🧪 Test d'Autonomie de LIA dans un Chat")
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
    learning_service = LearningService(config=support_config, memory_adapter=memory)
    
    # Passer le gemini_adapter à LLMAdapter pour activer l'autonomie
    core_adapter = LLMAdapter(
        core_config,
        use_memory=True,
        gemini_adapter=learning_service.gemini if hasattr(learning_service, 'gemini') else None,
        use_cognitive_planner=True  # Activer le nouveau système
    )
    
    print("✅ Services initialisés")
    print("✅ Autonomie activée (LIA peut solliciter Gemini)")
    print()
    
    # Test 1: Question qui devrait déclencher l'autonomie
    print("=" * 70)
    print("Test 1: Question nécessitant des connaissances externes")
    print("=" * 70)
    print()
    
    question1 = "Qu'est-ce que la mécanique quantique ? Explique-moi ce concept."
    print(f"👤 Vous: {question1}")
    print()
    print("⏳ LIA réfléchit et peut solliciter Gemini si nécessaire...")
    print()
    
    response1 = await core_adapter.generate(question1, session_id="test_autonomie")
    print(f"🤖 LIA: {response1}")
    print()
    
    # Test 2: Question de débat
    print("=" * 70)
    print("Test 2: Demande de débat")
    print("=" * 70)
    print()
    
    question2 = "Peux-tu débattre avec Gemini sur l'impact de l'IA sur l'emploi ?"
    print(f"👤 Vous: {question2}")
    print()
    print("⏳ LIA réfléchit et peut solliciter Gemini si nécessaire...")
    print()
    
    response2 = await core_adapter.generate(question2, session_id="test_autonomie")
    print(f"🤖 LIA: {response2}")
    print()
    
    # Test 3: Question simple (ne devrait pas déclencher Gemini)
    print("=" * 70)
    print("Test 3: Question simple (sans autonomie)")
    print("=" * 70)
    print()
    
    question3 = "Comment vas-tu aujourd'hui ?"
    print(f"👤 Vous: {question3}")
    print()
    
    response3 = await core_adapter.generate(question3, session_id="test_autonomie")
    print(f"🤖 LIA: {response3}")
    print()
    
    print("=" * 70)
    print("✅ Tests terminés")
    print("=" * 70)
    print()
    print("📝 Note: Si LIA a sollicité Gemini, vous devriez voir des logs")
    print("   indiquant '🤖 LIA décide de solliciter Gemini' dans les logs.")


if __name__ == "__main__":
    asyncio.run(test_autonomie_chat())

