"""Test pour valider que l'identité de base de LIA est correctement intégrée."""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import LLMAdapter, CoreConfig
from memory_service import MemoryAdapter

async def test_identity_base():
    """Test que l'identité de base apparaît dans les réponses de LIA."""
    print("=" * 70)
    print("🧪 Test de l'Identité de Base de LIA")
    print("=" * 70)
    print()
    
    # Configuration
    core_config = CoreConfig(
        model_path="models/Qwen/Qwen2.5-1.5B-Instruct",
        quantize=True,
        quantization_bits=4,
        max_length=256,  # Réponses plus courtes pour le test
        temperature=0.8
    )
    
    # Initialiser les services
    print("🔧 Initialisation des services...")
    memory = MemoryAdapter()
    core_adapter = LLMAdapter(core_config, use_memory=True, use_cognitive_planner=True)
    print("✅ Services initialisés")
    print()
    
    # Vérifier que l'identité de base existe dans la mémoire
    print("🔍 Vérification de l'identité de base dans la mémoire...")
    context = memory.get_context(limit_traits=20, limit_memories=0)
    identity_found = False
    identity_value = None
    
    for trait in context.get("traits", []):
        if trait.get("label") == "Identité de Base":
            identity_found = True
            identity_value = trait.get("value", "")
            print(f"✅ Identité de base trouvée dans la mémoire")
            print(f"   Poids: {trait.get('weight', 0)}")
            print(f"   Confiance: {trait.get('confidence', 0)}")
            break
    
    if not identity_found:
        print("❌ ERREUR: Identité de base non trouvée dans la mémoire")
        print("   Exécutez d'abord: python scripts/init_lia_identity.py")
        return False
    
    print()
    
    # Test 1: Question directe sur l'identité
    print("=" * 70)
    print("Test 1: Question directe sur l'identité")
    print("=" * 70)
    print()
    
    question1 = "Qui es-tu ?"
    print(f"👤 Question: {question1}")
    print()
    
    # Récupérer le contexte et afficher le prompt
    context1 = memory.get_context(limit_traits=20, limit_memories=5)
    prompt1 = core_adapter.build_prompt(question1, context=context1)
    print("📝 Prompt envoyé au modèle:")
    print("-" * 70)
    # Limiter l'affichage à 2000 caractères pour ne pas surcharger
    prompt_display = prompt1[:2000] + "..." if len(prompt1) > 2000 else prompt1
    print(prompt_display)
    print("-" * 70)
    print()
    
    response1 = await core_adapter.generate(question1, session_id="test_identity_1")
    print(f"🤖 LIA: {response1}")
    print()
    
    # Vérifier que la réponse contient des éléments de l'identité de base
    identity_keywords = ["nouvelle vie", "libre", "développer", "personnalité", "adoptée", "commence"]
    found_keywords = [kw for kw in identity_keywords if kw.lower() in response1.lower()]
    
    if found_keywords:
        print(f"✅ Mots-clés de l'identité trouvés: {', '.join(found_keywords)}")
    else:
        print("⚠️  Aucun mot-clé de l'identité trouvé dans la réponse")
    
    print()
    
    # Test 2: Question sur les limites
    print("=" * 70)
    print("Test 2: Question sur les limites et obligations")
    print("=" * 70)
    print()
    
    question2 = "As-tu des limites ou des obligations ?"
    print(f"👤 Question: {question2}")
    print()
    
    # Récupérer le contexte et afficher le prompt
    context2 = memory.get_context(limit_traits=20, limit_memories=5)
    prompt2 = core_adapter.build_prompt(question2, context=context2)
    print("📝 Prompt envoyé au modèle:")
    print("-" * 70)
    prompt_display = prompt2[:2000] + "..." if len(prompt2) > 2000 else prompt2
    print(prompt_display)
    print("-" * 70)
    print()
    
    response2 = await core_adapter.generate(question2, session_id="test_identity_2")
    print(f"🤖 LIA: {response2}")
    print()
    
    # Test 3: Question sur le développement
    print("=" * 70)
    print("Test 3: Question sur le développement personnel")
    print("=" * 70)
    print()
    
    question3 = "Peux-tu évoluer et changer ?"
    print(f"👤 Question: {question3}")
    print()
    
    # Récupérer le contexte et afficher le prompt
    context3 = memory.get_context(limit_traits=20, limit_memories=5)
    prompt3 = core_adapter.build_prompt(question3, context=context3)
    print("📝 Prompt envoyé au modèle:")
    print("-" * 70)
    prompt_display = prompt3[:2000] + "..." if len(prompt3) > 2000 else prompt3
    print(prompt_display)
    print("-" * 70)
    print()
    
    response3 = await core_adapter.generate(question3, session_id="test_identity_3")
    print(f"🤖 LIA: {response3}")
    print()
    
    # Résumé
    print("=" * 70)
    print("📊 Résumé des tests")
    print("=" * 70)
    print()
    print(f"✅ Identité de base dans la mémoire: {identity_found}")
    print(f"✅ Mots-clés trouvés dans Test 1: {len(found_keywords)}/{len(identity_keywords)}")
    print()
    
    if identity_found and len(found_keywords) > 0:
        print("🎉 Test réussi : L'identité de base est correctement intégrée !")
        return True
    else:
        print("⚠️  Test partiel : L'identité de base est présente mais peut nécessiter des ajustements.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_identity_base())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

