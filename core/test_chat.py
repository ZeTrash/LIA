"""Script de test pour chatter avec le modèle LLM (Qwen 2.5 1.5B Instruct)."""

import asyncio
import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurer le logging pour afficher les messages INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Format simple sans préfixe de logger
    stream=sys.stdout
)

from core import LLMAdapter, CoreConfig


async def main():
    """Fonction principale pour le chat."""
    print("=" * 60)
    print("LIA - Test de Chat")
    print("=" * 60)
    print()
    print("Initialisation du modèle...")
    print("(Cela peut prendre quelques secondes lors du premier chargement)")
    print("(Le nom exact du modèle chargé sera affiché ci-dessous)")
    print()
    
    # Créer la configuration pour Qwen 2.5 1.5B Instruct avec quantisation 4-bit
    config = CoreConfig(
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
        max_length=512,
        temperature=0.7,
        quantize=True,
        quantization_bits=4  # Quantisation 4-bit pour réduire l'utilisation mémoire
    )
    
    # Créer l'adaptateur avec système de planification cognitive activé
    try:
        adapter = LLMAdapter(config, use_cognitive_planner=True)
        print()
        print("[OK] Modèle chargé avec succès!")
        print("(Voir les logs ci-dessus pour le nom exact du modèle)")
        print()
    except Exception as e:
        print(f"[ERREUR] Erreur lors du chargement du modele: {e}")
        return
    
    print("Vous pouvez maintenant chatter avec LIA.")
    print("Tapez 'quit' ou 'exit' pour quitter.")
    print("Tapez 'clear' pour effacer le contexte.")
    print("-" * 60)
    print()
    
    # Contexte mémoire (vide pour le test)
    context = {
        "traits": [],
        "memories": [],
        "session_goals": []
    }
    
    while True:
        try:
            # Lire l'input utilisateur
            user_input = input("Vous: ").strip()
            
            if not user_input:
                continue
            
            # Commandes spéciales
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nAu revoir!")
                break
            
            if user_input.lower() == 'clear':
                context = {
                    "traits": [],
                    "memories": [],
                    "session_goals": []
                }
                print("[OK] Contexte efface.\n")
                continue
            
            # Générer la réponse
            print("LIA: ", end="", flush=True)
            try:
                response = await adapter.generate(
                    message=user_input,
                    context=context,
                    session_id="test-session"
                )
                print(response)
                print()
            except Exception as e:
                print(f"[ERREUR] {e}")
                print()
        
        except KeyboardInterrupt:
            print("\n\nAu revoir!")
            break
        except EOFError:
            print("\n\nAu revoir!")
            break


if __name__ == "__main__":
    asyncio.run(main())

