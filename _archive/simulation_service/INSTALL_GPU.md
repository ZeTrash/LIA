# Installation PyTorch avec support GPU (CUDA)

## Problème

Python 3.13 est très récent et PyTorch peut ne pas avoir de builds précompilés avec CUDA pour cette version.

## Solutions

### Option 1 : Utiliser Python 3.11 ou 3.12 (Recommandé)

1. Installez Python 3.11 ou 3.12 depuis [python.org](https://www.python.org/downloads/)
2. Créez un environnement virtuel :
   ```powershell
   python3.11 -m venv .venv
   .venv\Scripts\activate
   ```
3. Installez PyTorch avec CUDA :
   ```powershell
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### Option 2 : Installer PyTorch Nightly (Python 3.13)

Les builds nightly peuvent avoir le support CUDA pour Python 3.13 :

```powershell
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121
```

### Option 3 : Vérifier votre version CUDA

1. Vérifiez votre version CUDA :
   ```powershell
   nvidia-smi
   ```

2. Installez PyTorch avec la version CUDA correspondante :
   - **CUDA 12.1** : `--index-url https://download.pytorch.org/whl/cu121`
   - **CUDA 12.4** : `--index-url https://download.pytorch.org/whl/cu124`
   - **CUDA 11.8** : `--index-url https://download.pytorch.org/whl/cu118`

### Option 4 : Compiler depuis les sources (Avancé)

Si aucune des options ci-dessus ne fonctionne, vous pouvez compiler PyTorch depuis les sources, mais c'est complexe et long.

## Vérification

Après installation, vérifiez que CUDA est détecté :

```powershell
python check_gpu.py
```

Ou directement :

```python
import torch
print("CUDA disponible:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

## Note importante

Votre GPU **NVIDIA GeForce GTX 950M** est détecté par le système (CUDA 13.0). Une fois PyTorch avec CUDA installé, le système l'utilisera automatiquement et les performances seront **10-100x plus rapides** que sur CPU.
