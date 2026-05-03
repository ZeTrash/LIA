# Debug : Mémoire qui s'évapore après redémarrage

**Date** : 2024-12-19  
**Problème** : LIA ne se souvient pas des conversations précédentes après redémarrage du serveur

---

## Problème Observé

1. ✅ Les interactions sont bien stockées dans la base de données
2. ❌ Mais lors de la première génération après redémarrage, LIA ne se souvient pas des conversations précédentes
3. ⚠️ Il faut d'abord converser avec LIA, puis lui demander de se souvenir

---

## Diagnostic

### Logs Ajoutés

Des logs de debug ont été ajoutés pour diagnostiquer :

1. **Dans `core/llm_adapter.py`** :
   - Log lors de la récupération du contexte (ligne ~690)
   - Log lors de l'inclusion des interactions dans le prompt (lignes ~562, ~590)
   - Log du nombre d'interactions récupérées

2. **Dans `core/memory_activator.py`** :
   - Log du nombre d'interactions récupérées (ligne ~55)

### Comment Vérifier

1. **Activer les logs de debug** :
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Redémarrer le serveur** et regarder les logs :
   ```
   📚 Contexte récupéré via MemoryAdapter: X interactions
   📝 Inclusion de X interactions récentes dans le prompt
   ```

3. **Vérifier dans la base de données** :
   ```python
   from memory_service import MemoryAdapter
   memory = MemoryAdapter()
   context = memory.get_context(limit_interactions=5)
   print(f"Interactions: {len(context.get('recent_interactions', []))}")
   ```

---

## Causes Possibles

### 1. Contexte Non Récupéré ✅ (Corrigé)

**Problème** : Le paramètre `limit_interactions` n'était pas toujours passé à `get_context()`

**Solution** : Tous les appels à `get_context()` passent maintenant `limit_interactions=5`

### 2. Interactions Non Incluses dans le Prompt

**Vérification** : Les logs doivent montrer :
```
📝 Inclusion de X interactions récentes dans le prompt
```

Si ce log n'apparaît pas, les interactions ne sont pas incluses.

### 3. Prompt Tronqué

**Problème** : Si le prompt est trop long, il peut être tronqué et les interactions peuvent être coupées.

**Vérification** : Vérifier la longueur du prompt généré.

### 4. Format GGUF vs Qwen

**Problème** : Le format peut être différent selon le modèle utilisé.

**Vérification** : Vérifier quel format est utilisé (GGUF ou Qwen chat template).

---

## Solutions Appliquées

### 1. Logs de Diagnostic ✅

Ajout de logs pour tracer :
- Récupération du contexte
- Inclusion des interactions dans le prompt
- Nombre d'interactions récupérées

### 2. Correction des Appels à `get_context()` ✅

Tous les appels à `get_context()` passent maintenant `limit_interactions=5` :
- Ligne 694 : Fallback vers MemoryAdapter
- Ligne 716 : Re-récupération après création de souvenir
- Ligne 728 : Re-récupération après création de souvenir

### 3. Vérification de l'Inclusion ✅

Le code vérifie maintenant explicitement si les interactions sont présentes et les inclut dans le prompt.

---

## Test à Effectuer

### Test 1 : Vérifier les Interactions dans la Base

```python
from memory_service import MemoryAdapter
memory = MemoryAdapter()
context = memory.get_context(limit_interactions=5)
print(f"Interactions récentes: {len(context.get('recent_interactions', []))}")
for i, interaction in enumerate(context.get('recent_interactions', [])[:3], 1):
    print(f"{i}. {interaction.get('prompt', '')[:60]}...")
```

### Test 2 : Vérifier le Prompt Généré

Activer les logs de debug et vérifier que :
1. Les interactions sont récupérées
2. Elles sont incluses dans le prompt
3. Le prompt contient la section "=== NOTRE CONVERSATION RÉCENTE ==="

### Test 3 : Test Complet

1. Converser avec LIA (3-4 échanges)
2. Redémarrer le serveur
3. **Immédiatement** demander : "Te souviens-tu de notre dernière discussion ?"
4. Vérifier les logs pour voir si les interactions sont récupérées et incluses

---

## Prochaines Étapes

1. **Tester avec les logs activés** pour voir exactement ce qui se passe
2. **Vérifier le prompt généré** pour confirmer que les interactions sont incluses
3. **Si les interactions sont incluses mais LIA ne s'en souvient pas** :
   - Vérifier si le prompt est trop long et tronqué
   - Vérifier si le format est correct
   - Vérifier si LIA comprend bien le format

---

## Notes

- Les interactions sont stockées dans `interaction_logs` (table SQLite)
- Elles sont récupérées par ordre chronologique décroissant (plus récentes d'abord)
- Elles sont inversées dans le prompt pour avoir l'ordre chronologique (plus anciennes d'abord)
- Limité à 3 interactions dans le prompt pour économiser les tokens

---

**Date de création** : 2024-12-19

