# Guide d'installation et de test

## Problème rencontré

L'installation de `pydantic-core` nécessite Rust pour être compilé depuis la source. Python 3.13 est très récent et peut ne pas avoir de wheels précompilés disponibles.

## Solutions

### Option 1 : Installer les dépendances minimales pour les tests (RECOMMANDÉ)

Les tests de base (protocole, métriques, API) ne nécessitent pas `transformers`, `torch`, ou `bitsandbytes`. Ces dépendances sont uniquement nécessaires pour `test_local_llm_adapter.py`.

```powershell
cd simulation_service
pip install -r requirements-test.txt
```

Puis lancer les tests de base :

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_protocol.py tests/test_metrics.py tests/test_api.py -v
```

### Option 2 : Installer Rust correctement

Si vous voulez installer toutes les dépendances (y compris pour LocalLLMAdapter) :

1. **Installer Rust** : Téléchargez et installez depuis https://rustup.rs/
2. **Redémarrer le terminal** après l'installation
3. **Installer les dépendances complètes** :
   ```powershell
   pip install -r requirements.txt
   ```

### Option 3 : Utiliser une version plus récente de pydantic

Les versions plus récentes de pydantic peuvent avoir des wheels précompilés pour Python 3.13 :

```powershell
pip install --upgrade pydantic pydantic-core
pip install -r requirements-test.txt
```

### Option 4 : Utiliser Python 3.11 ou 3.12

Si vous avez des problèmes persistants avec Python 3.13, considérez utiliser Python 3.11 ou 3.12 qui ont un meilleur support pour les wheels précompilés.

## Lancer les tests

### Tous les tests (sauf LocalLLMAdapter si transformers n'est pas installé)

```powershell
cd simulation_service
python run_tests.py
```

### Tests spécifiques

```powershell
# Tests du protocole
$env:PYTHONPATH = "$PWD\src"
python -m pytest tests/test_protocol.py -v

# Tests des métriques
python -m pytest tests/test_metrics.py -v

# Tests de l'API
python -m pytest tests/test_api.py -v

# Tests LocalLLMAdapter (nécessite transformers/torch)
python -m pytest tests/test_local_llm_adapter.py -v
```

## Note importante

Les tests `test_local_llm_adapter.py` seront automatiquement ignorés (skipped) si `transformers` n'est pas installé. C'est le comportement attendu et normal.


