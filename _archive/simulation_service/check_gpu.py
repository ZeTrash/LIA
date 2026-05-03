"""Script pour vérifier la disponibilité du GPU et PyTorch."""

import sys

print("=" * 60)
print("DIAGNOSTIC GPU POUR LIA SIMULATION SERVICE")
print("=" * 60)
print()

# Vérifier PyTorch
try:
    import torch
    print(f"✅ PyTorch installé - version: {torch.__version__}")
    
    # Vérifier CUDA
    cuda_available = torch.cuda.is_available()
    print(f"🔍 CUDA disponible: {cuda_available}")
    
    if cuda_available:
        print(f"   ✅ Nombre de GPUs: {torch.cuda.device_count()}")
        print(f"   ✅ Nom du GPU: {torch.cuda.get_device_name(0)}")
        print(f"   ✅ Version CUDA: {torch.version.cuda}")
        print(f"   ✅ Version cuDNN: {torch.backends.cudnn.version()}")
        print()
        print("🎉 Le GPU sera utilisé automatiquement par LocalLLMAdapter !")
    else:
        print("   ⚠️  PyTorch n'a pas détecté de GPU")
        print()
        print("📋 Solutions possibles :")
        print("   1. Vérifiez que vous avez une carte graphique NVIDIA")
        print("   2. Vérifiez que les drivers NVIDIA sont installés : nvidia-smi")
        print()
        print("   3. Python 3.13 nécessite des builds PyTorch nightly ou spécifiques.")
        print("      Options :")
        print("      a) Installer PyTorch nightly avec CUDA (recommandé pour Python 3.13) :")
        print("         pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121")
        print("         pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu118")
        print("         pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130")
        print("      b) Utiliser Python 3.11 ou 3.12 (builds stables disponibles)")
        print("      c) Vérifier votre version CUDA avec nvidia-smi")
        print()
        print("💡 Le système utilisera le CPU par défaut si CUDA n'est pas disponible.")
        
except ImportError:
    print("❌ PyTorch n'est pas installé")
    print("   Installez-le avec: pip install torch")

print()
print("=" * 60)
