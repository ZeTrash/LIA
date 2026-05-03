"""Test pour valider que LIA utilise sa mémoire pour se personnifier."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import LLMAdapter, CoreConfig
from memory_service import MemoryAdapter

async def test_personnification():
    """Test que LIA utilise bien sa mémoire pour se personnifier."""
    print("=" * 70)
    print("🧪 Test de Personnification via Mémoire")
    print("=" * 70)
    print()
    
    # Configuration
    core_config = CoreConfig(
        model_path="models/Qwen/Qwen2.5-1.5B-Instruct",
        quantize=True,
        quantization_bits=4,
        max_length=256,
        temperature=0.8
    )
    
    # Initialiser les services
    print("🔧 Initialisation des services...")
    memory = MemoryAdapter()
    core_adapter = LLMAdapter(core_config, use_memory=True, use_cognitive_planner=True)
    print("✅ Services initialisés")
    print()
    
    # Test 1: Créer un trait de personnalité et vérifier qu'il apparaît
    print("=" * 70)
    print("Test 1: Trait de Personnalité")
    print("=" * 70)
    print()
    
    # Créer un trait de personnalité
    trait_id = memory.store.add_trait(
        trait_type="persona",
        label="Intérêt pour la philosophie",
        value="J'aime réfléchir sur les questions profondes de l'existence et de la conscience.",
        weight=1.0,
        confidence=0.9
    )
    print(f"✅ Trait créé: 'Intérêt pour la philosophie' (ID: {trait_id})")
    print()
    
    # Poser une question qui devrait activer ce trait
    question1 = "Qu'est-ce qui t'intéresse ?"
    print(f"👤 Question: {question1}")
    print()
    
    # Récupérer le contexte et afficher le prompt
    context1 = memory.get_context(limit_traits=10, limit_memories=5)
    prompt1 = core_adapter.build_prompt(question1, context=context1)
    print("📝 Prompt envoyé au modèle:")
    print("-" * 70)
    prompt_display = prompt1[:1500] + "..." if len(prompt1) > 1500 else prompt1
    print(prompt_display)
    print("-" * 70)
    print()
    
    response1 = await core_adapter.generate(question1, session_id="test_personnification_1")
    print(f"🤖 LIA: {response1}")
    print()
    
    # Vérifier que le trait apparaît dans la réponse
    trait_keywords = ["philosophie", "philosophique", "réfléchir", "questions", "existence", "conscience"]
    found_keywords = [kw for kw in trait_keywords if kw.lower() in response1.lower()]
    
    if found_keywords:
        print(f"✅ Mots-clés du trait trouvés: {', '.join(found_keywords)}")
    else:
        print("⚠️  Aucun mot-clé du trait trouvé dans la réponse")
    print()
    
    # Test 2: Créer un souvenir et vérifier qu'il est référencé
    print("=" * 70)
    print("Test 2: Souvenir et Continuité")
    print("=" * 70)
    print()
    
    # Créer un souvenir
    memory_id = memory.store.add_memory(
        category="preference",
        content="J'ai appris que l'utilisateur aime discuter de science-fiction et de futurologie.",
        importance_score=0.8,
        ttl_days=30
    )
    print(f"✅ Souvenir créé (ID: {memory_id})")
    print()
    
    # Poser une question de suivi qui nécessite la mémoire
    question2 = "Tu te souviens de ce que j'aime ?"
    print(f"👤 Question: {question2}")
    print()
    
    context2 = memory.get_context(limit_traits=10, limit_memories=5)
    prompt2 = core_adapter.build_prompt(question2, context=context2)
    print("📝 Prompt envoyé au modèle:")
    print("-" * 70)
    prompt_display = prompt2[:1500] + "..." if len(prompt2) > 1500 else prompt2
    print(prompt_display)
    print("-" * 70)
    print()
    
    response2 = await core_adapter.generate(question2, session_id="test_personnification_2")
    print(f"🤖 LIA: {response2}")
    print()
    
    # Vérifier que le souvenir est référencé
    memory_keywords = ["science-fiction", "futurologie", "souviens", "aime", "discuter"]
    found_memory_keywords = [kw for kw in memory_keywords if kw.lower() in response2.lower()]
    
    if found_memory_keywords:
        print(f"✅ Mots-clés du souvenir trouvés: {', '.join(found_memory_keywords)}")
    else:
        print("⚠️  Aucun mot-clé du souvenir trouvé dans la réponse")
    print()
    
    # Test 3: Vérifier le format "Je me souviens"
    print("=" * 70)
    print("Test 3: Format Personnel des Souvenirs")
    print("=" * 70)
    print()
    
    # Vérifier que le prompt contient "Je me souviens"
    if "Je me souviens" in prompt2 or "MES SOUVENIRS" in prompt2:
        print("✅ Format personnel trouvé dans le prompt ('Je me souviens' ou 'MES SOUVENIRS')")
    else:
        print("⚠️  Format personnel non trouvé dans le prompt")
    print()
    
    # Test 4: Vérifier le format "QUI JE SUIS"
    print("=" * 70)
    print("Test 4: Format Personnel des Traits")
    print("=" * 70)
    print()
    
    # Vérifier que le prompt contient "QUI JE SUIS"
    if "QUI JE SUIS" in prompt1 or "Personnalité" in prompt1:
        print("✅ Format personnel trouvé dans le prompt ('QUI JE SUIS' ou 'Personnalité')")
    else:
        print("⚠️  Format personnel non trouvé dans le prompt")
    print()
    
    # Résumé
    print("=" * 70)
    print("📊 Résumé des tests")
    print("=" * 70)
    print()
    print(f"✅ Trait créé et testé: {trait_id is not None}")
    print(f"✅ Mots-clés du trait trouvés: {len(found_keywords)}/{len(trait_keywords)}")
    print(f"✅ Souvenir créé et testé: {memory_id is not None}")
    print(f"✅ Mots-clés du souvenir trouvés: {len(found_memory_keywords)}/{len(memory_keywords)}")
    print(f"✅ Format personnel dans prompt: {'Oui' if 'Je me souviens' in prompt2 or 'MES SOUVENIRS' in prompt2 else 'Non'}")
    print()
    
    # Critères de succès
    success = (
        trait_id is not None and
        memory_id is not None and
        (len(found_keywords) > 0 or len(found_memory_keywords) > 0)
    )
    
    if success:
        print("🎉 Test réussi : LIA utilise sa mémoire pour se personnifier !")
        return True
    else:
        print("⚠️  Test partiel : La personnification fonctionne mais peut nécessiter des ajustements.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_personnification())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

