"""Script pour télécharger les modèles LLM localement."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import AutoModelForCausalLM, AutoTokenizer


def download_model_local(model_name: str = "Qwen/Qwen2.5-1.5B-Instruct", output_dir: str = "models"):
    """
    Télécharge le modèle GPT-2 et le stocke localement dans le projet.
    
    Args:
        model_name: Nom du modèle à télécharger (défaut: "gpt2")
        output_dir: Dossier de sortie (défaut: "models")
    """
    output_path = Path(output_dir) / model_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Téléchargement du modèle {model_name}...")
    print(f"Destination: {output_path.absolute()}")
    print()
    
    try:
        # Télécharger le modèle
        print("Téléchargement du modèle...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        model.save_pretrained(str(output_path))
        print("[OK] Modèle téléchargé et sauvegardé")
        
        # Télécharger le tokenizer
        print("Téléchargement du tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        tokenizer.save_pretrained(str(output_path))
        print("[OK] Tokenizer téléchargé et sauvegardé")
        
        print()
        print(f"[SUCCES] Modèle {model_name} téléchargé localement dans: {output_path.absolute()}")
        print()
        print("Vous pouvez maintenant utiliser ce modèle localement en configurant:")
        print(f'  config = CoreConfig(model_path="{output_path}")')
        
    except Exception as e:
        print(f"[ERREUR] Erreur lors du téléchargement: {e}")
        return False
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Télécharger un modèle LLM localement")
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Nom du modèle à télécharger (défaut: Qwen/Qwen2.5-1.5B-Instruct)"
    )
    parser.add_argument(
        "--output",
        default="models",
        help="Dossier de sortie (défaut: models)"
    )
    
    args = parser.parse_args()
    
    success = download_model_local(args.model, args.output)
    sys.exit(0 if success else 1)

