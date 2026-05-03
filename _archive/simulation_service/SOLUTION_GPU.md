# Solution pour utiliser le GPU avec Python 3.13

## Problème identifié

Votre système :
- ✅ GPU détecté : **NVIDIA GeForce GTX 950M** (CUDA 13.0)
- ✅ Drivers NVIDIA installés
- ❌ **PyTorch n'a pas de builds CUDA précompilés pour Python 3.13**

L'erreur `ERROR: Could not find a version that satisfies the requirement torch` confirme que PyTorch avec CUDA n'est pas disponible pour Python 3.13 sur les index officiels.

## Solutions

### Solution 1 : Utiliser Python 3.12 (RECOMMANDÉ)

Python 3.12 a un excellent support PyTorch avec CUDA :

1. **Installer Python 3.12** depuis [python.org](https://www.python.org/downloads/)
   - Téléchargez Python 3.12.x (pas 3.13)
   - Installez-le (vous pouvez garder Python 3.13 aussi)

2. **Créer un environnement virtuel avec Python 3.12** :
   ```powershell
   # Trouver le chemin de Python 3.12 (exemple)
   C:\Python312\python.exe -m venv .venv
   .venv\Scripts\activate
   ```

3. **Installer PyTorch avec CUDA** :
   ```powershell
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

4. **Vérifier** :
   ```powershell
   python -c "import torch; print('CUDA:', torch.cuda.is_available())"
   ```

### Solution 2 : Utiliser PyTorch Nightly Builds (Python 3.13)

Les builds nightly de PyTorch supportent Python 3.13 avec CUDA :

1. **Installer PyTorch Nightly avec CUDA** :
   ```powershell
   # Pour CUDA 12.1
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121
   
   # Pour CUDA 11.8 (si cu121 ne fonctionne pas)
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu118
   
   # Pour CUDA 13.0 (si disponible)
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130
   ```

2. **Vérifier** :
   ```powershell
   python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Version:', torch.__version__)"
   ```

**Note** : Les builds nightly peuvent être moins stables que les versions officielles, mais ils offrent le support Python 3.13.

### Solution 3 : Utiliser le CPU pour l'instant

Le système fonctionne déjà sur CPU. Les performances seront plus lentes mais fonctionnelles :
- Latence : ~7-15 secondes par génération (vs ~0.5-1s sur GPU)
- Mémoire : ~1.2GB (vs ~500MB sur GPU avec quantisation)

## Vérification actuelle

Pour vérifier l'état actuel :

```powershell
cd "c:\Users\achim\Desktop\Espace de travail\LIA\simulation_service"
& C:\Python313\python.exe check_gpu.py
```

## Note importante

Le code dans `adapters.py` détecte **automatiquement** le GPU dès qu'il est disponible. Une fois PyTorch avec CUDA installé (avec Python 3.12), le système utilisera automatiquement votre GTX 950M sans modification de code.

**Performance attendue avec GPU** :
- ⚡ 10-50x plus rapide pour la génération de texte
- 💾 Moins de mémoire utilisée avec quantisation INT4/INT8
- 🎯 Meilleure expérience utilisateur
