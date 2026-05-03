"""Script pour télécharger un modèle GGUF depuis HuggingFace."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_gguf_model(
    model_file: str = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
    repo_id: str = "bartowski/Qwen2.5-1.5B-Instruct-GGUF",
    output_dir: str = "models"
):
    """
    Télécharge un modèle GGUF depuis HuggingFace.
    
    Args:
        model_file: Nom du fichier .gguf à télécharger
        repo_id: ID du repository HuggingFace
        output_dir: Dossier de sortie (défaut: models)
    
    Returns:
        Chemin vers le fichier téléchargé
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    final_path = output_path / model_file
    
    print("=" * 60)
    print(f"Téléchargement du modèle GGUF: {model_file}")
    print(f"Repository: {repo_id}")
    print(f"Destination: {final_path.absolute()}")
    print("=" * 60)
    print()
    
    # Vérifier si le fichier existe déjà
    if final_path.exists():
        print(f"✅ Le modèle existe déjà: {final_path}")
        print(f"   Taille: {final_path.stat().st_size / (1024**3):.2f} GB")
        return str(final_path)
    
    try:
        # Essayer d'utiliser huggingface_hub
        try:
            from huggingface_hub import hf_hub_download
            print("Utilisation de huggingface_hub...")
            
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=model_file,
                local_dir=str(output_path),
                local_dir_use_symlinks=False
            )
            
            # Si le fichier est dans un sous-dossier, le déplacer
            downloaded_path = Path(downloaded_path)
            if downloaded_path.parent != output_path:
                final_path = output_path / model_file
                if downloaded_path != final_path:
                    downloaded_path.rename(final_path)
                    print(f"✅ Fichier déplacé vers: {final_path}")
                else:
                    print(f"✅ Fichier déjà au bon endroit: {final_path}")
            else:
                final_path = downloaded_path
            
            print()
            print(f"[SUCCÈS] Modèle téléchargé: {final_path.absolute()}")
            print(f"   Taille: {final_path.stat().st_size / (1024**3):.2f} GB")
            return str(final_path)
            
        except ImportError:
            print("⚠️  huggingface_hub non disponible, tentative avec wget...")
            raise ImportError("huggingface_hub requis")
            
    except ImportError:
        # Fallback: utiliser wget/curl
        print("Tentative avec wget...")
        try:
            import subprocess
            import urllib.parse
            
            # Construire l'URL HuggingFace
            base_url = f"https://huggingface.co/{repo_id}/resolve/main/{model_file}"
            
            print(f"URL: {base_url}")
            print("Téléchargement en cours... (cela peut prendre plusieurs minutes)")
            
            # Utiliser wget si disponible
            result = subprocess.run(
                ["wget", "-O", str(final_path), base_url],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print()
                print(f"[SUCCÈS] Modèle téléchargé: {final_path.absolute()}")
                print(f"   Taille: {final_path.stat().st_size / (1024**3):.2f} GB")
                return str(final_path)
            else:
                # Essayer avec curl
                print("wget a échoué, tentative avec curl...")
                result = subprocess.run(
                    ["curl", "-L", "-o", str(final_path), base_url],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print()
                    print(f"[SUCCÈS] Modèle téléchargé: {final_path.absolute()}")
                    print(f"   Taille: {final_path.stat().st_size / (1024**3):.2f} GB")
                    return str(final_path)
                else:
                    raise Exception(f"Échec du téléchargement: {result.stderr}")
                    
        except FileNotFoundError:
            raise Exception(
                "Aucun outil de téléchargement trouvé. "
                "Installez huggingface_hub: pip install huggingface_hub"
            )
    
    except Exception as e:
        print(f"[ERREUR] Erreur lors du téléchargement: {e}")
        print()
        print("Solutions alternatives:")
        print("1. Installer huggingface_hub: pip install huggingface_hub")
        print("2. Télécharger manuellement depuis:")
        print(f"   https://huggingface.co/{repo_id}/tree/main")
        print(f"   Et placer le fichier dans: {output_path.absolute()}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Télécharger un modèle GGUF depuis HuggingFace"
    )
    parser.add_argument(
        "--model",
        default="Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        help="Nom du fichier .gguf à télécharger (défaut: Qwen2.5-1.5B-Instruct-Q4_K_M.gguf)"
    )
    parser.add_argument(
        "--repo",
        default="bartowski/Qwen2.5-1.5B-Instruct-GGUF",
        help="Repository HuggingFace (défaut: bartowski/Qwen2.5-1.5B-Instruct-GGUF)"
    )
    parser.add_argument(
        "--output",
        default="models",
        help="Dossier de sortie (défaut: models)"
    )
    
    args = parser.parse_args()
    
    try:
        model_path = download_gguf_model(
            model_file=args.model,
            repo_id=args.repo,
            output_dir=args.output
        )
        print()
        print("✅ Téléchargement terminé !")
        print()
        print("Vous pouvez maintenant utiliser ce modèle avec:")
        print(f'  config = CoreConfig(gguf_model_path="{model_path}")')
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)

