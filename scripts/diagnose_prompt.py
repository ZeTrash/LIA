"""Script de diagnostic pour inspecter un prompt LIA (sections, tailles, format, contexte mémoire).

Usage:
  python scripts/diagnose_prompt.py --message "Qui es-tu ?" --session-id "test_session"
  python scripts/diagnose_prompt.py --message "Conscience vs mémoire ?" --limit-interactions 5
"""

import sys
import argparse
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import LLMAdapter, CoreConfig
from memory_service import MemoryAdapter

def diagnose_prompt():
    """Diagnostique le prompt généré (format, sections, tailles) et optionnellement teste une génération."""
    print("=" * 70)
    print("🔍 Diagnostic du Prompt - LIA")
    print("=" * 70)
    print()

    parser = argparse.ArgumentParser(description="Diagnose LIA prompt building and context injection.")
    parser.add_argument("--message", type=str, default="Qui es-tu ?", help="Message utilisateur à injecter")
    parser.add_argument("--session-id", type=str, default="diagnostic_test", help="Session id pour récupérer le contexte")
    parser.add_argument("--limit-traits", type=int, default=20, help="Nombre max de traits")
    parser.add_argument("--limit-memories", type=int, default=5, help="Nombre max de souvenirs")
    parser.add_argument("--limit-interactions", type=int, default=5, help="Nombre max d'interactions récentes")
    parser.add_argument("--no-generate", action="store_true", help="N'exécute pas de génération réelle")
    args = parser.parse_args()
    
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
    core_adapter = LLMAdapter(core_config, use_memory=True)
    print("✅ Services initialisés")
    print()
    
    # 1. Vérifier la mémoire
    print("=" * 70)
    print("1. Vérification de la mémoire")
    print("=" * 70)
    print()
    
    context = memory.get_context(
        limit_traits=args.limit_traits,
        limit_memories=args.limit_memories,
        limit_interactions=args.limit_interactions,
    )
    
    print(f"Nombre de traits dans le contexte: {len(context.get('traits', []))}")
    print(f"Nombre de souvenirs dans le contexte: {len(context.get('memories', []))}")
    print(f"Nombre d'interactions récentes dans le contexte: {len(context.get('recent_interactions', []))}")
    print()
    
    identity_found = False
    for trait in context.get("traits", []):
        print(f"Trait: {trait.get('label')} (type: {trait.get('type')}, poids: {trait.get('weight')})")
        if trait.get("label") == "Identité de Base":
            identity_found = True
            print(f"  ✅ IDENTITÉ DE BASE TROUVÉE")
            print(f"  Valeur: {trait.get('value')[:200]}...")
            print()
    
    if not identity_found:
        print("❌ ERREUR: Identité de base non trouvée dans le contexte !")
        print("   Exécutez: python scripts/init_lia_identity.py")
        return
    
    print()
    
    # 2. Générer un prompt pour voir ce qui est inclus
    print("=" * 70)
    print("2. Génération du prompt")
    print("=" * 70)
    print()
    
    prompt = core_adapter.build_prompt(args.message, context=context)
    estimated_tokens = len(prompt) // 4  # heuristique utilisée ailleurs dans le projet
    
    print("PROMPT GÉNÉRÉ:")
    print("-" * 70)
    print(prompt)
    print("-" * 70)
    print()
    print(f"Taille prompt: {len(prompt)} caractères (~{estimated_tokens} tokens estimés)")
    print()
    
    # 3. Vérifier si l'identité de base est dans le prompt
    print("=" * 70)
    print("3. Vérification de la présence de l'identité de base")
    print("=" * 70)
    print()
    
    identity_keywords = ["nouvelle vie", "libre", "développer", "adoptée", "commence"]
    found_in_prompt = [kw for kw in identity_keywords if kw.lower() in prompt.lower()]

    # Le prompt actuel utilise généralement "=== IDENTITÉ ===" (et pas forcément "IDENTITÉ DE BASE")
    has_identity_section = ("=== IDENTITÉ ===" in prompt) or ("=== IDENTITE ===" in prompt)
    if has_identity_section:
        print("✅ Section '=== IDENTITÉ ===' trouvée dans le prompt")
    else:
        print("❌ Section '=== IDENTITÉ ===' NON trouvée dans le prompt")
    
    if found_in_prompt:
        print(f"✅ Mots-clés trouvés: {', '.join(found_in_prompt)}")
    else:
        print("⚠️  Aucun mot-clé de l'identité trouvé dans le prompt")
    
    print()
    
    # 4. Vérifier le format Qwen (chat template)
    print("=" * 70)
    print("4. Vérification du format Qwen (chat template)")
    print("=" * 70)
    print()
    
    if hasattr(core_adapter, 'tokenizer') and core_adapter.tokenizer is not None:
        if hasattr(core_adapter.tokenizer, 'apply_chat_template') and core_adapter.tokenizer.chat_template:
            print("✅ Le tokenizer supporte le chat template")
            print("   Le prompt sera formaté selon le template Qwen")
        else:
            print("⚠️  Le tokenizer ne supporte pas le chat template")
            print("   Le format classique sera utilisé")
    else:
        print("⚠️  Tokenizer non disponible")
    
    print()
    
    # 5. Test avec génération réelle
    print("=" * 70)
    print("5. Test de génération réelle")
    print("=" * 70)
    print()
    
    import asyncio
    
    async def test_generation():
        response = await core_adapter.generate(args.message, session_id=args.session_id)
        print(f"Question: {args.message}")
        print(f"Réponse: {response}")
        print()
        
        # Vérifier les mots-clés dans la réponse
        found_in_response = [kw for kw in identity_keywords if kw.lower() in response.lower()]
        if found_in_response:
            print(f"✅ Mots-clés de l'identité trouvés dans la réponse: {', '.join(found_in_response)}")
        else:
            print("⚠️  Aucun mot-clé de l'identité trouvé dans la réponse")
            print("   La réponse ne reflète pas l'identité de base")
    
    if args.no_generate:
        print("⏭️  Génération réelle désactivée (--no-generate)")
    else:
        asyncio.run(test_generation())

if __name__ == "__main__":
    try:
        diagnose_prompt()
    except Exception as e:
        print(f"\n\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

