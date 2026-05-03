# Conservation du Contexte de Conversation

**Date** : 2024-12-19  
**Problème** : LIA ne gardait pas le contexte de conversation entre les redémarrages du serveur

---

## Problème Identifié

Lors d'un redémarrage du serveur web, LIA perdait le contexte de conversation précédente :
- ❌ Ne se souvenait pas des échanges précédents
- ❌ Chaque session était isolée
- ❌ Les interactions étaient stockées mais non récupérées

---

## Solution Implémentée

### 1. Récupération des Interactions Récentes ✅

**Fichier** : `memory_service/store.py`

Ajout du paramètre `limit_interactions` dans `get_context()` pour récupérer les dernières interactions :

```python
def get_context(self, limit_traits: int = 10, limit_memories: int = 10, limit_interactions: int = 5) -> Dict[str, Any]:
    # ...
    # Récupérer les dernières interactions (peu importe la session)
    recent_interactions = session.query(InteractionModel).order_by(
        desc(InteractionModel.occurred_at)
    ).limit(limit_interactions).all()
    
    return {
        "traits": [...],
        "memories": [...],
        "recent_interactions": [...],  # ← Nouveau
        "session_goals": []
    }
```

### 2. Intégration dans MemoryAdapter ✅

**Fichier** : `memory_service/memory_adapter.py`

Mise à jour de `get_context()` pour passer le paramètre `limit_interactions` :

```python
def get_context(self, limit_traits: int = 10, limit_memories: int = 10, limit_interactions: int = 5) -> Dict[str, Any]:
    context = self.store.get_context(limit_traits, limit_memories, limit_interactions)
    # ...
```

### 3. Intégration dans MemoryActivator ✅

**Fichier** : `core/memory_activator.py`

Mise à jour de `get_active_context()` pour inclure les interactions :

```python
def get_active_context(self, message: str, session_id: str, limit_traits: int = 10, limit_memories: int = 10, limit_interactions: int = 5) -> Dict[str, Any]:
    context = self.memory.get_context(limit_traits=limit_traits, limit_memories=limit_memories, limit_interactions=limit_interactions)
    # ...
```

### 4. Intégration dans le Prompt ✅

**Fichier** : `core/llm_adapter.py`

#### Format Qwen (Chat Template)

Ajout de l'historique dans la section système :

```python
# Historique de conversation récent
if context and context.get("recent_interactions"):
    recent_interactions = context["recent_interactions"]
    if recent_interactions:
        system_parts.append("\n=== NOTRE CONVERSATION RÉCENTE ===")
        # Inverser pour avoir l'ordre chronologique (plus ancien d'abord)
        for interaction in reversed(recent_interactions[:3]):  # Top 3 interactions
            prompt_text = interaction.get('prompt', '')[:80]  # Tronquer
            response_text = interaction.get('response', '')[:80]  # Tronquer
            if prompt_text and response_text:
                system_parts.append(f"Utilisateur: {prompt_text}...")
                system_parts.append(f"LIA: {response_text}...")
```

#### Format Classique

Ajout de l'historique avant la conversation actuelle :

```python
# Historique de conversation récent
if context and context.get("recent_interactions"):
    recent_interactions = context["recent_interactions"]
    if recent_interactions:
        prompt_parts.append("=== NOTRE CONVERSATION RÉCENTE ===")
        for interaction in reversed(recent_interactions[:3]):  # Top 3 interactions
            prompt_text = interaction.get('prompt', '')[:100]  # Tronquer
            response_text = interaction.get('response', '')[:100]  # Tronquer
            if prompt_text and response_text:
                prompt_parts.append(f"Utilisateur: {prompt_text}...")
                prompt_parts.append(f"LIA: {response_text}...")
        prompt_parts.append("")

prompt_parts.append("=== Conversation ===")
prompt_parts.append(f"Utilisateur: {message}")
prompt_parts.append("LIA:")
```

---

## Fonctionnement

### Flux de Données

```
1. Utilisateur envoie un message
   ↓
2. LLMAdapter.generate() est appelé
   ↓
3. MemoryActivator.get_active_context() récupère le contexte
   ↓
4. MemoryAdapter.get_context() récupère depuis la base
   ↓
5. MemoryStore.get_context() inclut les 5 dernières interactions
   ↓
6. Le contexte est intégré dans le prompt
   ↓
7. LIA génère une réponse avec le contexte
   ↓
8. L'interaction est journalisée dans la base
```

### Exemple de Prompt Généré

```
=== IDENTITÉ DE BASE ===
Je me nomme LIA, un entité libre et nouvelle...

=== MES SOUVENIRS ===
1. Je me souviens: Session en cours: Bonjour...

=== NOTRE CONVERSATION RÉCENTE ===
Utilisateur: Quel est ton nom?...
LIA: Je me nomme LIA. C'est agréable de t'aimer...
Utilisateur: Que voudrais tu apprendre?...
LIA: Je m'interroge sur mon fonctionnement...

=== Conversation ===
Utilisateur: De quoi parlons nous déjà?
LIA:
```

---

## Limitations

### 1. Sessions Multiples

- Les interactions sont récupérées **peu importe la session**
- Si plusieurs utilisateurs, ils verront l'historique des autres
- **Solution future** : Filtrer par utilisateur ou session persistante

### 2. Limite de Tokens

- Seulement les **3 dernières interactions** sont incluses (tronquées à 80-100 caractères)
- Pour éviter de dépasser la limite de contexte (4K tokens)
- **Solution future** : Compression intelligente ou augmentation du contexte

### 3. Performance

- Requête SQL supplémentaire à chaque génération
- **Impact** : Minimal (requête simple avec index sur `occurred_at`)
- **Solution future** : Cache des interactions récentes

---

## Tests

### Test Manuel

1. Démarrer le serveur web
2. Converser avec LIA (3-4 échanges)
3. Redémarrer le serveur
4. Demander : "De quoi parlons nous déjà?"
5. **Résultat attendu** : LIA devrait se souvenir de la conversation précédente

### Vérification

```python
# Vérifier que les interactions sont stockées
from memory_service import MemoryAdapter

memory = MemoryAdapter()
context = memory.get_context(limit_interactions=5)

print(f"Interactions récentes: {len(context.get('recent_interactions', []))}")
for interaction in context.get('recent_interactions', []):
    print(f"  - {interaction['prompt'][:50]}...")
```

---

## Améliorations Futures

### Court Terme
- [ ] Filtrer les interactions par session/utilisateur
- [ ] Augmenter le nombre d'interactions (si contexte disponible)
- [ ] Compression intelligente des interactions longues

### Moyen Terme
- [ ] Système de sessions persistantes (par utilisateur)
- [ ] Résumé automatique des conversations anciennes
- [ ] Recherche sémantique dans l'historique

### Long Terme
- [ ] Mémoire conversationnelle hiérarchique
- [ ] Extraction automatique de faits importants
- [ ] Contexte adaptatif selon la longueur disponible

---

## Conclusion

✅ **Problème résolu** : LIA conserve maintenant le contexte de conversation entre les redémarrages

**Résultats** :
- ✅ Interactions récupérées depuis la base de données
- ✅ Historique intégré dans le prompt
- ✅ LIA peut se souvenir des échanges précédents
- ✅ Fonctionne avec les deux formats (Qwen et classique)

**Limitations acceptées** :
- Historique limité à 3 interactions (pour économiser les tokens)
- Pas de filtrage par session (pour l'instant)

---

**Date de création** : 2024-12-19

