# Autonomie de LIA : Solliciter Gemini de Manière Autonome

**Date** : 2024-12-19  
**Statut** : ✅ Implémenté

---

## Problème Initial

LIA avait conscience de son environnement et savait qu'elle pouvait solliciter Gemini, mais **elle ne pouvait pas vraiment le faire** dans un chat normal. Dans le test `test_lia_gemini.py`, c'était le code qui appelait Gemini, pas LIA elle-même.

---

## Solution Implémentée

### 1. Intégration de `AutonomousActionManager` dans `LLMAdapter`

**Fichier** : `core/llm_adapter.py`

**Modifications** :
- Import de `AutonomousActionManager`
- Initialisation automatique si `gemini_adapter` est fourni
- Méthode `generate()` utilise maintenant `AutonomousActionManager` si disponible
- Méthode `_generate_internal()` créée pour éviter la récursion

**Code** :
```python
def __init__(self, config: Optional[CoreConfig] = None, use_memory: bool = True, gemini_adapter=None):
    # ... code existant ...
    
    # Initialiser le gestionnaire d'actions autonomes
    self.autonomous_manager = None
    if AUTONOMOUS_ACTIONS_AVAILABLE and gemini_adapter:
        self.autonomous_manager = AutonomousActionManager(
            memory_adapter=self.memory,
            gemini_adapter=gemini_adapter
        )
```

### 2. Méthode `generate()` avec Autonomie

**Fichier** : `core/llm_adapter.py`

**Fonctionnement** :
- Par défaut, `use_autonomy=True`
- Si `autonomous_manager` est disponible, il intercepte le message
- Détecte si Gemini devrait être sollicité (mots-clés)
- Si oui, appelle Gemini et intègre la réponse dans le contexte
- Sinon, génère une réponse normale

**Code** :
```python
async def generate(
    self,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    use_autonomy: bool = True
) -> str:
    # Utiliser le gestionnaire d'actions autonomes si disponible
    if use_autonomy and self.autonomous_manager:
        return await self.autonomous_manager.process_with_autonomy(
            message=message,
            core_adapter=self,
            session_id=session_id or "default"
        )
    # ... génération normale ...
```

### 3. Détection Automatique

**Fichier** : `core/autonomous_actions.py`

**Mots-clés déclencheurs** :
- "qu'est-ce que", "comment fonctionne", "explique", "informe"
- "recherche", "débat", "antithèse", "quelle est", "définis"
- "informations sur", "en savoir plus", "apprendre"

**Fonctionnement** :
```python
def _should_query_gemini(self, message: str) -> bool:
    keywords = [
        "qu'est-ce que", "comment fonctionne", "explique", "informe", 
        "recherche", "débat", "antithèse", "quelle est", "définis",
        "informations sur", "en savoir plus", "apprendre"
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)
```

---

## Utilisation

### Dans un Chat Normal

**Exemple** :
```python
from core import LLMAdapter, CoreConfig
from support import LearningService, SupportConfig
from memory_service import MemoryAdapter

# Configuration
core_config = CoreConfig(
    model_path="models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    use_gguf=True
)

support_config = SupportConfig()
support_config.load_from_file("config/api.conf")

# Initialiser les services
memory = MemoryAdapter()
learning_service = LearningService(config=support_config, memory_adapter=memory)

# Passer gemini_adapter pour activer l'autonomie
core_adapter = LLMAdapter(
    core_config,
    use_memory=True,
    gemini_adapter=learning_service.gemini  # ← Important !
)

# LIA peut maintenant solliciter Gemini de manière autonome
response = await core_adapter.generate(
    "Qu'est-ce que la mécanique quantique ?",
    session_id="chat_session"
)
```

### Désactiver l'Autonomie

Si vous voulez désactiver l'autonomie pour une requête spécifique :
```python
response = await core_adapter.generate(
    message,
    session_id=session_id,
    use_autonomy=False  # ← Désactiver l'autonomie
)
```

---

## Flux d'Exécution

```
1. Utilisateur envoie un message
   ↓
2. LLMAdapter.generate() est appelé
   ↓
3. AutonomousActionManager intercepte le message
   ↓
4. Détection : Le message contient-il des mots-clés ?
   ├─ OUI → Appeler Gemini
   │   ↓
   │   Intégrer la réponse de Gemini dans le contexte
   │   ↓
   │   Générer la réponse finale avec le contexte enrichi
   │
   └─ NON → Générer une réponse normale
```

---

## Test

**Fichier** : `tests/test_autonomie_chat.py`

**Exécution** :
```bash
python tests/test_autonomie_chat.py
```

**Ce que le test vérifie** :
1. ✅ LIA peut solliciter Gemini pour des questions nécessitant des connaissances externes
2. ✅ LIA peut solliciter Gemini pour des débats
3. ✅ LIA ne sollicite pas Gemini pour des questions simples

---

## Logs

Quand LIA sollicite Gemini, vous verrez dans les logs :
```
🤖 LIA décide de solliciter Gemini pour: Qu'est-ce que la mécanique quantique ?...
```

---

## Limitations Actuelles

1. **Détection basée sur mots-clés** : La détection est simple (mots-clés). Une amélioration future pourrait utiliser l'analyse sémantique.

2. **Extraction de question** : Pour l'instant, le message entier est envoyé à Gemini. Une amélioration future pourrait extraire uniquement la question pertinente.

3. **Pas de confirmation** : LIA sollicite Gemini automatiquement sans demander confirmation. Cela pourrait être ajouté comme option.

---

## Prochaines Améliorations

1. **Analyse sémantique** : Utiliser des embeddings pour détecter si une question nécessite Gemini
2. **Extraction intelligente** : Extraire uniquement la question pertinente du message
3. **Confirmation utilisateur** : Demander confirmation avant de solliciter Gemini (optionnel)
4. **Cache des réponses** : Mémoriser les réponses de Gemini pour éviter les appels répétés

---

## Conclusion

✅ **LIA peut maintenant solliciter Gemini de manière autonome** dans un chat normal, pas seulement dans les tests.

L'autonomie est activée automatiquement si :
- `gemini_adapter` est fourni à `LLMAdapter`
- Le message contient des mots-clés déclencheurs
- `use_autonomy=True` (par défaut)

**Date de création** : 2024-12-19

