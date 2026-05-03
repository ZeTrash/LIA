# Documentation : Système de Streaming de Chunks et Réponses Structurées

## Vue d'ensemble

Ce document décrit l'implémentation du système de **streaming en temps réel** des étapes de processus internes de LIA, ainsi que la structuration des réponses en deux types distincts : **chunks de processus** et **réponse finale**.

## Contexte et Objectifs

### Problème initial

Avant cette implémentation, l'utilisateur ne voyait que la réponse finale de LIA, sans visibilité sur le processus cognitif interne (décisions de menu, consultations mémoire, requêtes externes, etc.).

### Objectifs

1. **Transparence du processus** : Permettre à l'utilisateur de suivre en temps réel les étapes internes de LIA
2. **Différenciation visuelle** : Distinguer clairement les étapes de processus de la réponse finale
3. **Streaming temps réel** : Afficher les chunks au fur et à mesure de leur génération, sans attendre la fin
4. **Regroupement cohérent** : Tous les éléments d'une même requête utilisateur dans un seul bloc visuel

## Architecture

### 1. Modèle de Données : `ResponseChunk`

**Fichier** : `core/cognitive_models.py`

```python
class ResponseChunkType(str, Enum):
    """Type de fragment de réponse à exposer à l'interface."""
    PROCESS = "process"   # Étape de processus interne (menu, décision, action)
    RESPONSE = "response" # Sortie utilisateur finale (ou partielle)

@dataclass
class ResponseChunk:
    """Fragment structuré de réponse pour suivi de processus."""
    type: ResponseChunkType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Types de chunks** :
- `PROCESS` : Étapes internes (ex: "Répondre à la requête de l'utilisateur", "Consulter la mémoire")
- `RESPONSE` : Réponse finale destinée à l'utilisateur

### 2. Génération et Streaming : `LLMAdapter`

**Fichier** : `core/llm_adapter.py`

#### Méthode principale : `generate_with_trace`

```python
async def generate_with_trace(
    self,
    message: str,
    session_id: Optional[str] = None,
    use_autonomy: bool = True,
    use_cognitive_planner: Optional[bool] = None,
    process_callback: Optional[Callable[[Any], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """
    Génère une réponse + une trace structurée du processus interne.
    
    Returns:
        {
          "response": str,
          "trace": List[ResponseChunk (as dict)],
        }
    """
```

**Fonctionnalités** :
- Génère la réponse via le planificateur cognitif
- Collecte tous les `ResponseChunk` dans `_last_trace_chunks`
- Appelle `process_callback` en temps réel pour chaque chunk `PROCESS`
- Retourne la trace complète à la fin

#### Création des chunks PROCESS

Les chunks `PROCESS` sont créés à deux moments dans `_generate_with_planner` :

1. **Pour les actions passées** (historique) :
```python
# Libellé court de l'action, utilisé pour l'affichage des étapes de processus
process_label = _describe_action(past_action)
chunk = ResponseChunk(
    type=ResponseChunkType.PROCESS,
    content=process_label,
    metadata={
        "action_type": past_action.type.value,
        "iteration": i,
    },
)
trace_chunks.append(chunk)
if process_callback:
    await process_callback(chunk)
```

2. **Pour le choix courant** (décision immédiate) :
```python
process_label = _describe_action(choice)
chunk = ResponseChunk(
    type=ResponseChunkType.PROCESS,
    content=process_label,
    metadata={
        "action_type": choice.type.value,
        "iteration": i,
    },
)
trace_chunks.append(chunk)
if process_callback:
    await process_callback(chunk)
```

**Logging** :
- `📤 [LLM_ADAPTER] Chunk PROCESS créé` : Chunk créé
- `✅ [LLM_ADAPTER] Chunk PROCESS envoyé au web via callback` : Chunk envoyé

### 3. Interface Utilisateur : `UserChannel`

**Fichier** : `interfaces/user_channel.py`

#### Méthode : `send_message_structured`

```python
async def send_message_structured(
    self,
    message: str,
    session_id: Optional[str] = None,
    use_autonomy: bool = True,
    process_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
```

**Fonctionnalités** :
- Appelle `LLMAdapter.generate_with_trace`
- Transforme les `ResponseChunk` en dictionnaires sérialisables
- Transmet les chunks `PROCESS` au `process_callback` en temps réel
- Retourne la réponse finale et la trace complète

**Callback interne** :
```python
async def _internal_process_callback(chunk_obj: Any):
    chunk_dict = {
        "type": chunk_obj.type.value,
        "content": chunk_obj.content,
        "metadata": chunk_obj.metadata or {},
    }
    await process_callback(chunk_dict)
```

### 4. Interface Web : WebSocket et Frontend

**Fichier backend** : `web_interface/app_chat.py`

#### Endpoint WebSocket : `/ws/{session_id}`

```python
async def process_callback(chunk: dict):
    """Callback appelé à chaque étape de processus."""
    if chunk.get("type") != "process":
        return
    await manager.send_message({
        "type": "lia_process",
        "content": chunk.get("content", ""),
        "metadata": chunk.get("metadata", {}),
        "timestamp": datetime.now().isoformat()
    }, session_id)
```

**Messages WebSocket** :
- `lia_process` : Chunk de processus reçu
- `lia_response_start` : Début de la réponse finale
- `lia_chunk` : Chunk de réponse finale (streaming)
- `lia_response_end` : Fin de la réponse finale

**Fichier frontend** : `web_interface/static/chat.html`

#### Gestion des messages

```javascript
case 'lia_process':
    addProcessMessage(data.content, 'lia_process', data.timestamp);
    break;

case 'lia_response_start':
    removeThinkingIndicatorFromContainer();
    currentLiaResponseId = addStreamingMessage('lia', data.timestamp);
    break;

case 'lia_chunk':
    if (currentLiaResponseId) {
        appendChunkToMessage(currentLiaResponseId, data.content);
    }
    break;

case 'lia_response_end':
    if (currentLiaResponseId) {
        finalizeStreamingMessage(currentLiaResponseId);
        currentLiaResponseId = null;
    }
    closeProcessContainer();
    break;
```

## Interface Utilisateur : Bloc Unique d'Interaction

### Concept : Un seul bloc par requête utilisateur

Tous les éléments découlant d'une même requête utilisateur sont regroupés dans **un seul bloc visuel** aligné comme un message LIA :

```
┌─────────────────────────────────────┐
│ 🤖 LIA                               │
│ ┌─────────────────────────────────┐ │
│ │ 🧠 Répondre à la requête...     │ │ ← Steps (processus)
│ │ ❓ Question à Gemini...         │ │
│ │ 💡 Réponse de Gemini...         │ │
│ │ ... (trois points animés)        │ │ ← Indicateur réflexion
│ ├─────────────────────────────────┤ │
│ │ Bonjour ! Comment puis-je...    │ │ ← Réponse finale
│ └─────────────────────────────────┘ │
│ 20:50                               │
└─────────────────────────────────────┘
```

### Structure HTML

```html
<div class="message lia lia-interaction" id="process_container_...">
    <div class="message-avatar">🤖</div>
    <div class="message-content">
        <div class="lia-interaction-steps">
            <!-- Chunks de processus ici -->
            <div class="lia-interaction-step">
                <div class="lia-step-badge lia">🧠</div>
                <div class="lia-step-text">Répondre à la requête...</div>
            </div>
            <!-- Indicateur de réflexion -->
            <div class="lia-thinking-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
        <div class="lia-interaction-response">
            <!-- Réponse finale en streaming -->
            <div class="lia-answer">
                <span class="streaming-content"></span>
                <span class="streaming-cursor">▋</span>
            </div>
        </div>
        <div class="message-time">20:50</div>
    </div>
</div>
```

### Fonctions JavaScript clés

#### `getOrCreateProcessContainer(timestamp)`

Crée ou récupère le conteneur unique pour une requête utilisateur.

```javascript
function getOrCreateProcessContainer(timestamp) {
    if (currentProcessContainerId) {
        const container = document.getElementById(currentProcessContainerId);
        if (container) return container;
    }
    // Créer nouveau conteneur
    const containerDiv = document.createElement('div');
    containerDiv.className = 'message lia lia-interaction';
    currentProcessContainerId = 'process_container_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    // ... structure HTML ...
    return containerDiv;
}
```

#### `addProcessMessage(content, type, timestamp)`

Ajoute un chunk de processus dans la section `lia-interaction-steps`.

```javascript
function addProcessMessage(content, type, timestamp) {
    // Retirer l'indicateur de réflexion existant
    removeThinkingIndicatorFromContainer();
    
    const container = getOrCreateProcessContainer(timestamp);
    const steps = container.querySelector('.lia-interaction-steps');
    
    const stepDiv = document.createElement('div');
    stepDiv.className = 'lia-interaction-step';
    // Badge + couleur par type
    // ...
    steps.appendChild(stepDiv);
    
    // Ajouter l'indicateur de réflexion après le chunk
    addThinkingIndicatorToContainer();
}
```

#### `addThinkingIndicatorToContainer()`

Ajoute l'animation de réflexion (trois points) après chaque chunk.

```javascript
function addThinkingIndicatorToContainer() {
    const container = document.getElementById(currentProcessContainerId);
    const steps = container.querySelector('.lia-interaction-steps');
    
    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'lia-thinking-indicator';
    indicatorDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    steps.appendChild(indicatorDiv);
}
```

### Styles CSS

#### Conteneur principal

```css
.message.lia.lia-interaction {
    margin: 12px 0;
    display: flex;
    gap: 12px;
    animation: fadeInUp 0.3s ease-out;
}

.message.lia.lia-interaction .message-content {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 14px 16px;
    max-width: 70%;
}
```

#### Section des steps (processus)

```css
.lia-interaction-steps {
    margin-bottom: 12px;
}

.lia-interaction-step {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 0;
    font-size: 11px;
    color: #616161;
}

.lia-step-badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex-shrink: 0;
}

.lia-step-badge.lia {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

#### Indicateur de réflexion

```css
.lia-interaction-steps .lia-thinking-indicator {
    display: flex;
    gap: 4px;
    padding: 8px 0;
    margin-top: 4px;
    justify-content: flex-start;
    align-items: center;
}

.lia-interaction-steps .lia-thinking-indicator .typing-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #999;
    animation: typing 1.4s infinite;
}

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-10px); }
}
```

#### Section de réponse finale

```css
.lia-interaction-response {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #e0e0e0;
}

.lia-interaction-response .lia-answer {
    color: #212121;
    font-size: 15px;
    line-height: 1.7;
    font-weight: 400;
}
```

## Flux de Données Complet

### 1. Requête utilisateur

```
Utilisateur → WebSocket → app_chat.py → UserChannel.send_message_structured()
```

### 2. Génération avec trace

```
UserChannel → LLMAdapter.generate_with_trace()
    ↓
_generate_with_planner()
    ↓
Pour chaque décision/action :
    - Créer ResponseChunk(type=PROCESS, content="...")
    - Ajouter à trace_chunks
    - Appeler process_callback(chunk) ← STREAMING TEMPS RÉEL
    ↓
Quand RESPOND choisi :
    - Générer réponse finale
    - Créer ResponseChunk(type=RESPONSE, content="...")
    - Ajouter à trace_chunks
```

### 3. Streaming vers le frontend

```
process_callback (LLMAdapter)
    ↓
_internal_process_callback (UserChannel)
    ↓
process_callback (app_chat.py)
    ↓
WebSocket.send_message({type: "lia_process", ...})
    ↓
Frontend: case 'lia_process'
    ↓
addProcessMessage() → Ajoute dans .lia-interaction-steps
    ↓
addThinkingIndicatorToContainer() → Affiche animation réflexion
```

### 4. Réponse finale

```
LLMAdapter retourne response + trace
    ↓
UserChannel retourne {lia_response, trace, ...}
    ↓
app_chat.py envoie lia_response_start
    ↓
Frontend: removeThinkingIndicatorFromContainer()
    ↓
Frontend: Affiche réponse dans .lia-interaction-response
    ↓
app_chat.py envoie lia_chunk (streaming)
    ↓
Frontend: appendChunkToMessage()
    ↓
app_chat.py envoie lia_response_end
    ↓
Frontend: finalizeStreamingMessage() + closeProcessContainer()
```

## Types de Chunks Supportés

### Chunks PROCESS

| Type | Badge | Couleur | Description |
|------|-------|---------|-------------|
| `lia_process` | 🧠 | Violet (#667eea) | Décision interne de LIA |
| `process_start` | 🚀 | Bleu | Début d'un processus |
| `process_end` | ✅ | Vert | Fin d'un processus |
| `gemini_query` | ❓ | Orange | Question envoyée à Gemini |
| `gemini_response` | 💡 | Vert | Réponse de Gemini |
| `gemini_error` | ⚠️ | Rouge | Erreur Gemini |

### Chunks RESPONSE

- Réponse finale destinée à l'utilisateur
- Affichée dans `.lia-interaction-response`
- Streaming caractère par caractère avec curseur animé

## Résolution du Problème de Streaming Temps Réel

### Problème initial

Les chunks étaient créés pendant la génération, mais n'arrivaient au frontend qu'à la fin, car la génération GGUF était **bloquante** et empêchait l'event loop de traiter les callbacks WebSocket.

### Solution : Threading asynchrone

**Fichier** : `web_interface/app_chat.py`

```python
async def process_callback(chunk: dict):
    """Callback appelé à chaque étape de processus."""
    # Envoi immédiat via WebSocket (non bloquant)
    await manager.send_message({
        "type": "lia_process",
        "content": chunk.get("content", ""),
        ...
    }, session_id)
```

La génération se fait dans un thread séparé, permettant à l'event loop FastAPI de traiter les messages WebSocket immédiatement.

## Logs et Debugging

### Backend

- `📤 [LLM_ADAPTER] Chunk PROCESS créé` : Chunk créé dans le planner
- `✅ [LLM_ADAPTER] Chunk PROCESS envoyé au web via callback` : Chunk transmis au callback
- `🌐 [WEB] Envoi immédiat du chunk PROCESS au WebSocket` : Message WebSocket envoyé
- `✅ [WEB] Chunk PROCESS envoyé au WebSocket` : Confirmation d'envoi

### Frontend

- `📥 [FRONTEND] Réception immédiate du chunk PROCESS` : Message reçu
- `✅ [FRONTEND] Chunk PROCESS affiché dans le DOM` : Chunk ajouté au DOM

## Points d'Extension Futurs

1. **Chunks supplémentaires** : Ajouter d'autres types de chunks (métriques, vérifications, etc.)
2. **Interactivité** : Permettre à l'utilisateur d'interagir avec les steps (expand/collapse)
3. **Historique** : Sauvegarder la trace complète pour analyse ultérieure
4. **Performance** : Optimiser le rendu pour de très longues traces

## Fichiers Modifiés

- `core/cognitive_models.py` : Ajout de `ResponseChunkType` et `ResponseChunk`
- `core/llm_adapter.py` : Implémentation de `generate_with_trace` et création des chunks
- `interfaces/user_channel.py` : Méthode `send_message_structured` avec callback
- `web_interface/app_chat.py` : Endpoint WebSocket avec `process_callback`
- `web_interface/static/chat.html` : Interface frontend avec bloc unique et animation

## Références

- `docs/memory_performing/exemple_process.md` : Exemple de processus interne
- `docs/memory_performing/IMPLEMENTATION_PHASE_EXEMPLE_PROCESS.md` : Phase d'implémentation précédente

