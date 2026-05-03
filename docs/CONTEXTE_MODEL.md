# Configuration du Contexte du Modèle

**Date** : 2024-12-19  
**Contexte** : Avertissement sur la fenêtre de contexte du modèle GGUF

---

## Avertissement Observé

```
llama_context: n_ctx_per_seq (4096) < n_ctx_train (131072)
```

### Signification

- **`n_ctx_train (131072)`** : Le modèle Llama-3.2-3B a été entraîné avec un contexte de **128K tokens** (131072)
- **`n_ctx_per_seq (4096)`** : On utilise seulement **4K tokens** (4096) pour économiser la RAM

### Impact

✅ **C'est normal et acceptable** :
- Le modèle fonctionne correctement avec 4K tokens
- On économise beaucoup de RAM (chaque token de contexte consomme de la mémoire)
- 4K tokens est largement suffisant pour nos besoins actuels

⚠️ **Limitation** :
- Si on a besoin de plus de contexte (prompts très longs), on peut augmenter `n_ctx`
- Mais cela consommera plus de RAM

---

## Configuration Actuelle

**Fichier** : `core/llm_adapter.py` (ligne 345)

```python
n_ctx = min(self.config.max_prompt_length, 4096)  # Limiter à 4K pour économiser RAM
```

**Raison** : Limitation à 4096 tokens pour économiser la RAM sur CPU.

---

## Options

### Option 1 : Garder 4K (Recommandé) ✅

**Avantages** :
- ✅ Économie de RAM
- ✅ Suffisant pour la plupart des cas d'usage
- ✅ Performance optimale

**Inconvénients** :
- ⚠️ Limite pour prompts très longs (> 4K tokens)

### Option 2 : Augmenter à 8K

**Modification** :
```python
n_ctx = min(self.config.max_prompt_length, 8192)  # 8K tokens
```

**Impact** :
- 📈 Consommation RAM : ~2x plus
- ✅ Supporte prompts plus longs
- ⚠️ Peut être plus lent

### Option 3 : Augmenter à 16K

**Modification** :
```python
n_ctx = min(self.config.max_prompt_length, 16384)  # 16K tokens
```

**Impact** :
- 📈 Consommation RAM : ~4x plus
- ✅ Supporte prompts très longs
- ⚠️ Peut être significativement plus lent

### Option 4 : Utiliser la Capacité Maximale (128K)

**Modification** :
```python
n_ctx = min(self.config.max_prompt_length, 131072)  # 128K tokens (capacité max)
```

**Impact** :
- 📈 Consommation RAM : ~32x plus (peut nécessiter 16GB+ RAM)
- ✅ Supporte prompts extrêmement longs
- ⚠️ Peut être très lent sur CPU
- ⚠️ Risque de manque de mémoire

---

## Recommandation

### Pour l'Usage Actuel

✅ **Garder 4K tokens** est recommandé car :
- Nos prompts actuels font ~500-2000 tokens
- On a largement assez de marge (2000+ tokens pour la réponse)
- Performance optimale sur CPU

### Si Besoin de Plus de Contexte

Si vous avez besoin de plus de contexte (prompts très longs, beaucoup de souvenirs) :

1. **Augmenter progressivement** : 8K → 16K → 32K
2. **Surveiller la RAM** : Utiliser `htop` ou `free -h`
3. **Tester les performances** : Vérifier que la génération reste rapide

---

## Calcul de la Consommation RAM

**Formule approximative** :
```
RAM ≈ n_ctx × n_layers × n_embd × 2 bytes × 2 (KV cache)
```

Pour Llama-3.2-3B :
- `n_layers` ≈ 28
- `n_embd` ≈ 3072

**Estimation** :
- **4K tokens** : ~1.4 GB RAM
- **8K tokens** : ~2.8 GB RAM
- **16K tokens** : ~5.6 GB RAM
- **128K tokens** : ~45 GB RAM (⚠️ très élevé)

---

## Comment Modifier

### Dans `core/llm_adapter.py`

```python
# Ligne 345
# Avant
n_ctx = min(self.config.max_prompt_length, 4096)  # Limiter à 4K pour économiser RAM

# Après (exemple pour 8K)
n_ctx = min(self.config.max_prompt_length, 8192)  # 8K tokens
```

### Via Configuration

On pourrait ajouter un paramètre dans `CoreConfig` :

```python
# Dans core/config.py
max_context_tokens: int = 4096  # Limite du contexte pour GGUF

# Dans core/llm_adapter.py
n_ctx = min(self.config.max_prompt_length, self.config.max_context_tokens)
```

---

## Conclusion

✅ **L'avertissement est normal et peut être ignoré**

- Le modèle fonctionne correctement avec 4K tokens
- C'est un compromis optimal entre performance et capacité
- On peut augmenter si nécessaire, mais cela consommera plus de RAM

**Recommandation** : Garder 4K tokens pour l'instant, augmenter seulement si nécessaire.

---

**Date de création** : 2024-12-19

