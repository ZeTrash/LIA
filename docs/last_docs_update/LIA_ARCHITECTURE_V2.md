# LIA — Architecture V2 : Le Cerveau Modulaire
> Document de conception — Mise à jour majeure pour AMD Developer Hackathon 2026  
> Auteur : Mohamad ASIMO | Projet : LIA (Autonomous Agent)  
> Version : 2.0.0-draft

---

## 1. Vision Générale

### 1.1 Concept

LIA (Laboratoire d'Intelligence Artificielle) évolue d'un agent à **LLM unique** vers une **architecture cérébrale modulaire** inspirée du système nerveux humain.

Dans la V1, un seul modèle (Qwen 2.5-7B GGUF) assumait tous les rôles : comprendre, mémoriser, raisonner, coder, communiquer. Cette contrainte était architecturale, imposée par les limites du VPS Oracle (CPU-only, RAM limitée).

Avec l'accès aux **AMD Instinct MI300X (192 GB VRAM)** via AMD Developer Cloud, cette limite tombe. LIA peut désormais faire tourner **plusieurs LLMs spécialisés simultanément**, chacun expert dans son domaine, coordonnés par un superviseur central.

### 1.2 Métaphore Biologique

```
Cerveau Humain                    LIA V2
──────────────────────────────────────────────────────
Cortex préfrontal (décision)  →  NeuralRouter (superviseur)
Cortex moteur (action)        →  CodeBrain (exécution/auto-amélioration)
Cortex auditif                →  AudioBrain (son/parole)
Cortex visuel                 →  VisionBrain (images/vidéo)
Hippocampe (mémoire)          →  MemoryBrain (mémoire hiérarchique)
Amygdale (identité/émotions)  →  IdentityBrain (noyau stable)
Système nerveux autonome      →  InteroceptionBrain (monitoring)
Langage (Broca/Wernicke)      →  LangBrain (communication)
```

---

## 2. Architecture du Cerveau Modulaire

### 2.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ENTRÉE UTILISATEUR                          │
│                (texte / voix / image / fichier code)                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        NEURAL ROUTER                                │
│              (Superviseur — Qwen 1.5B ultra-rapide)                 │
│                                                                     │
│  • Classifie l'intention de l'entrée                                │
│  • Décompose en sous-tâches si nécessaire                           │
│  • Dispatche vers les modules spécialisés                           │
│  • Agrège les réponses des modules                                  │
│  • Gère les conflits et priorités                                   │
└──┬────────┬────────┬────────┬────────┬────────┬────────┬────────────┘
   │        │        │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│LANG  │ │CODE  │ │VISION│ │AUDIO │ │MEMO  │ │IDENT │ │INTERO    │
│BRAIN │ │BRAIN │ │BRAIN │ │BRAIN │ │BRAIN │ │BRAIN │ │CEPTION   │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘
   │        │
   │        ▼
   │   ┌──────────────────────────────────────────────────────────┐
   │   │              SANDBOX D'AUTO-AMÉLIORATION                 │
   │   │  (environnement isolé pour test du code auto-généré)     │
   │   └──────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SORTIE FINALE                               │
│              (texte / code / audio / image / action)                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Le NeuralRouter (Superviseur)

**Rôle :** C'est le chef d'orchestre. Il reçoit toute entrée et décide comment la traiter.

**Modèle recommandé :** `Qwen2.5-1.5B-Instruct` (déjà dans la codebase comme `model_name` par défaut dans `CoreConfig`)

**Pourquoi un modèle léger ?**
- Le routing est une tâche de classification, pas de génération complexe
- Latence minimale pour chaque décision
- Économie de VRAM pour les modules spécialisés

**Responsabilités :**

```python
class NeuralRouter:
    """
    Superviseur central du Cerveau Modulaire de LIA.
    
    Hérite de l'architecture existante :
    - CognitivePlanner (core/cognitive_planner.py) → logique de décision
    - ActionExecutor (core/action_executor.py) → dispatching
    - PatternLearner (core/pattern_learner.py) → apprentissage des routes
    """
    
    def classify_intent(self, input: Any) -> IntentClassification:
        """
        Classifie l'intention de l'entrée.
        
        Retourne:
            - type: LANG | CODE | VISION | AUDIO | MEMORY | IDENTITY | SYSTEM
            - sub_tasks: liste de sous-tâches si décomposition nécessaire
            - priority: urgence (0-1)
            - multi_brain: True si plusieurs modules nécessaires
        """
    
    def dispatch(self, intent: IntentClassification) -> BrainDispatchPlan:
        """
        Crée un plan de dispatch vers les modules appropriés.
        Peut activer plusieurs modules en parallèle (ex: LANG + MEMORY).
        """
    
    def aggregate(self, responses: Dict[BrainType, BrainResponse]) -> FinalResponse:
        """
        Agrège les réponses de plusieurs modules en une réponse cohérente.
        Utilise IdentityBrain pour s'assurer de la cohérence de ton/style.
        """
```

**Intégration avec l'existant :**

Le `NeuralRouter` est une **évolution naturelle** du `LLMAdapter` actuel. La boucle cognitive (`_generate_with_planner`) devient le cœur du dispatcher. Les `ActionType` existants (B1, B2, G1...) sont étendus pour mapper vers les modules.

---

### 2.3 LangBrain — Module Communication

**Rôle :** Génération de langage naturel, réponses conversationnelles, gestion du style et du ton.

**Modèle recommandé :** `Qwen2.5-7B-Instruct` (modèle actuel de LIA) ou `Qwen2.5-14B-Instruct` (sur MI300X, la VRAM le permet)

**Ce qu'il fait :**
- Génère les réponses textuelles finales
- Maintient la cohérence conversationnelle (contexte = mémoire à court terme)
- Applique le style de LIA (défini par IdentityBrain)
- Gère le multilinguisme (Qwen excelle en multilingue)

**Intégration avec l'existant :**

```python
# Dans llm_adapter.py, la méthode _generate_internal devient :
class LangBrain:
    model: Qwen2_5_7B  # ou 14B sur MI300X
    
    # Existant — à conserver tel quel :
    def build_prompt(self, message, context) -> str: ...
    def _generate_gguf(self, prompt) -> str: ...
    def _clean_response(self, response) -> str: ...
    def _generate_gguf_stream(self, prompt) -> AsyncIterator[str]: ...
```

---

### 2.4 CodeBrain — Module Coding & Auto-Amélioration

**Rôle :** C'est le module le plus stratégique. Il permet à LIA de **se recoder elle-même**.

**Modèle recommandé :** `Qwen2.5-Coder-7B-Instruct` (spécialisé coding, déjà dans la famille Qwen)

**Capacités :**
- Génération de code Python, JavaScript, Bash
- Analyse et refactoring de code existant
- **Auto-amélioration de LIA elle-même** (voir section 2.4.1)
- Création de nouveaux modules/fonctionnalités à la demande

#### 2.4.1 Système d'Auto-Amélioration (Self-Coding Loop)

C'est la fonctionnalité la plus ambitieuse. Voici comment elle fonctionne :

**Prérequis pour l'auto-amélioration :**

1. **Conscience architecturale** — LIA doit connaître sa propre structure

```python
class ArchitectureGraph:
    """
    Graphe de la propre architecture de LIA.
    LIA peut le consulter pour comprendre comment elle est construite.
    
    Contenu :
    - Liste des modules (NeuralRouter, LangBrain, CodeBrain...)
    - Interfaces de chaque module (inputs/outputs)
    - Dépendances inter-modules
    - Contraintes et limites connues
    - Historique des auto-modifications (version control interne)
    """
    
    modules: Dict[str, ModuleSpec]
    interfaces: Dict[str, InterfaceSpec]
    constraints: List[Constraint]
    changelog: List[SelfModification]
```

2. **Sandbox isolé** — Le nouveau code doit être testé avant intégration

```python
class SelfCodingSandbox:
    """
    Environnement isolé pour tester les auto-modifications de LIA.
    
    Inspiré du module autonomy/ existant (autonomy/__init__.py)
    """
    
    async def test_modification(self, new_code: str, target_module: str) -> SandboxResult:
        """
        Teste une modification de code dans un environnement isolé.
        
        Étapes :
        1. Créer un environnement Docker/subprocess isolé
        2. Injecter le nouveau code
        3. Lancer les tests existants (core/tests/)
        4. Mesurer les métriques (latence, mémoire, qualité réponse)
        5. Comparer avec la version précédente
        6. Retourner le résultat avec recommandation (intégrer / rejeter)
        """
    
    async def rollback(self, version: str) -> bool:
        """
        Retourne à une version précédente si l'auto-modification a causé des problèmes.
        Utilise le changelog de ArchitectureGraph.
        """
```

3. **Evaluator** — Juge si l'amélioration est réellement meilleure

```python
class SelfImprovementEvaluator:
    """
    Évalue si une auto-modification améliore réellement LIA.
    
    Hérite de SelfVerifier (core/self_verifier.py) existant.
    """
    
    def evaluate(self, before: BenchmarkResult, after: BenchmarkResult) -> EvaluationResult:
        """
        Critères d'évaluation :
        - Qualité des réponses (pertinence, cohérence)
        - Performance (latence, tokens utilisés)
        - Stabilité (pas de régression sur les tests existants)
        - Alignement avec l'identité (IdentityBrain ne doit pas changer)
        """
```

**Le flux complet d'auto-amélioration :**

```
1. LIA détecte un problème ou une opportunité d'amélioration
   (ex: "Je génère souvent des réponses trop longues")
   
2. NeuralRouter route vers CodeBrain avec l'intent SELF_IMPROVE
   
3. CodeBrain analyse l'architecture via ArchitectureGraph
   ("Quel module est responsable de la longueur des réponses ?")
   
4. CodeBrain génère une modification de code
   (modifie _clean_response() ou max_length dans CoreConfig)
   
5. SelfCodingSandbox teste la modification en isolation
   
6. SelfImprovementEvaluator compare avant/après
   
7a. Si amélioration validée → intégration + changelog
7b. Si régression détectée → rollback automatique + log du problème
   
8. MemoryBrain mémorise l'expérience (succès ou échec)
```

---

### 2.5 VisionBrain — Module Vision & Multimodal

**Rôle :** Traitement et compréhension d'images, vidéos, et documents visuels.

**Modèle recommandé :** `Qwen2.5-VL-7B-Instruct` (multimodal, déjà dans la famille Qwen)

**Capacités :**
- Analyse d'images (description, OCR, extraction d'informations)
- Traitement de captures d'écran (ex: LIA comprend son interface web)
- Analyse de diagrammes et code visuel
- Inspection visuelle de son propre environnement (conscience visuelle)

**Note AMD :** Le MI300X avec 192 GB VRAM est particulièrement adapté aux modèles multimodaux lourds. C'est explicitement mentionné dans le Track 3 du hackathon.

---

### 2.6 AudioBrain — Module Son & Parole

**Rôle :** Compréhension et génération audio (STT/TTS).

**Modèles recommandés :**
- STT : `Whisper-large-v3` (OpenAI, open-source, excellent multilingue)
- TTS : `Kokoro-82M` ou `Parler-TTS` (open-source, qualité native)

**Capacités :**
- Transcription vocale → texte (input)
- Synthèse texte → voix (output)
- Détection de langue automatique
- Compréhension du ton/émotion dans la voix

**Intégration :**

```python
class AudioBrain:
    stt_model: WhisperModel  # speech-to-text
    tts_model: KokoroModel   # text-to-speech
    
    async def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Audio → texte, avec détection de langue."""
    
    async def synthesize(self, text: str, voice_style: str = "lia_default") -> AudioBytes:
        """Texte → audio, avec le style vocal de LIA."""
```

---

### 2.7 MemoryBrain — Module Mémoire Hiérarchique

**Rôle :** Évolution du système de mémoire existant vers une architecture hiérarchique complète.

**Modèles associés :** Pas de LLM dédié — utilise des embeddings et SQLite (existant)

**Architecture mémoire V2 :**

```
MemoryBrain V2 (extension de memory_service/ existant)
│
├── Mémoire à court terme (Working Memory)
│   ├── Contexte de conversation courante (session)
│   ├── Résultats des actions récentes (execution_results)
│   └── État du NeuralRouter (current intent, active modules)
│
├── Mémoire à long terme (Long-term Memory)
│   ├── Souvenirs épisodiques (MemoryRank V2 existant — phrase_memory_processor.py)
│   ├── Faits sémantiques (knowledge base)
│   └── Patterns appris (table patterns existante)
│
├── Mémoire procédurale (Procedural Memory)
│   ├── Séquences d'actions optimales (PatternLearner existant)
│   ├── Skills acquis (nouvelles capacités auto-générées par CodeBrain)
│   └── Workflows mémorisés (comment résoudre un type de problème)
│
└── Mémoire architecturale (Self-Knowledge)
    ├── ArchitectureGraph (nouveau — pour auto-amélioration)
    ├── Changelog des auto-modifications
    └── Métriques de performance historiques (CognitiveMetrics existant)
```

**Intégration avec l'existant :**

La plupart de cette architecture **existe déjà** dans le code :
- `memory_service/memory_rank.py` → mémoire à long terme (épisodique)
- `memory_service/phrase_memory_processor.py` → MemoryRank V2
- `core/pattern_learner.py` → mémoire procédurale (patterns)
- `core/cognitive_metrics.py` → métriques historiques

Ce qui est **nouveau** :
- `MemoryBrain.working_memory` — état courant de la session
- `MemoryBrain.architecture_graph` — auto-connaissance de LIA

---

### 2.8 IdentityBrain — Module Identité (Noyau Stable)

**Rôle :** Gardien de l'identité et des valeurs de LIA. **Ce module ne change PAS lors des auto-améliorations.**

**Modèle associé :** Pas de LLM dédié — basé sur les traits en mémoire + règles fixes

**Principe fondamental :** L'identité de LIA est la seule partie **immuable** du système. Peu importe ce que CodeBrain modifie, IdentityBrain reste stable.

**Contenu :**

```python
class IdentityBrain:
    """
    Noyau identitaire stable de LIA.
    
    Basé sur l'existant :
    - scripts/init_lia_identity.py (initialisation)
    - core/cognitive_safeguards.py (limites éthiques)
    - memory_service/store.py (traits stockés en DB)
    """
    
    # Traits fondamentaux (immuables)
    core_values: List[str]          # Ce que LIA est fondamentalement
    ethical_boundaries: List[Rule]  # Ce que LIA ne fera jamais
    personality_traits: List[Trait] # Sa façon d'être (curiosité, empathie, etc.)
    
    # Style de communication (modifiable uniquement par l'utilisateur)
    communication_style: CommunicationStyle
    voice_characteristics: VoiceProfile  # Pour AudioBrain
    
    def validate_response(self, response: str) -> IdentityValidationResult:
        """
        Vérifie qu'une réponse est cohérente avec l'identité de LIA.
        Appelé par NeuralRouter avant chaque output final.
        Hérite de SelfVerifier.verify() existant.
        """
    
    def validate_self_modification(self, modification: SelfModification) -> bool:
        """
        Vérifie qu'une auto-modification ne touche pas à l'identité.
        Gate keeper du SelfCodingSandbox.
        """
```

---

### 2.9 InteroceptionBrain — Module Monitoring Interne

**Rôle :** LIA monitore son propre état de santé, comme le système nerveux autonome chez l'humain.

**Modèle associé :** Pas de LLM — basé sur métriques système

**Inspiré de :** `core/cognitive_metrics.py` et `core/cognitive_safeguards.py` existants

**Métriques surveillées :**

```python
class InteroceptionBrain:
    """
    Conscience de l'état interne de LIA.
    
    Surveille en temps réel :
    """
    
    # Ressources système
    gpu_utilization: float         # % VRAM utilisée (MI300X)
    gpu_temperature: float         # Température GPU
    inference_latency: float       # Temps de réponse moyen
    token_throughput: float        # Tokens/seconde
    
    # État cognitif
    memory_pressure: float         # Saturation de la mémoire
    active_modules: List[BrainType] # Modules actuellement actifs
    queue_depth: int               # Requêtes en attente
    
    # Santé des modules
    module_health: Dict[BrainType, HealthStatus]
    last_error_by_module: Dict[BrainType, Optional[Exception]]
    
    # Budget (existant dans CognitiveSafeguards)
    token_budget_remaining: int
    time_budget_remaining: float
    
    def get_health_report(self) -> HealthReport:
        """Rapport de santé complet — exposé via l'interface web."""
    
    def should_throttle(self, module: BrainType) -> bool:
        """Doit-on ralentir un module ? (surcharge, température...)"""
    
    def alert(self, severity: AlertLevel, message: str) -> None:
        """Alerte interne — mémorisée dans MemoryBrain."""
```

---

## 3. Migration depuis la V1

### 3.1 Ce qui est conservé (la base solide)

| Composant V1 | Rôle dans V2 |
|---|---|
| `core/llm_adapter.py` | Devient le cœur de `LangBrain` + `NeuralRouter` |
| `core/cognitive_planner.py` | Logique de décision du `NeuralRouter` |
| `core/action_executor.py` | Dispatcher du `NeuralRouter` |
| `core/pattern_learner.py` | Mémoire procédurale de `MemoryBrain` |
| `core/cognitive_safeguards.py` | Gate keeper de `IdentityBrain` |
| `core/cognitive_metrics.py` | Base de `InteroceptionBrain` |
| `core/self_verifier.py` | Validateur de `IdentityBrain` |
| `memory_service/` | Couche persistence de `MemoryBrain` |
| `memory_service/phrase_memory_processor.py` | MemoryRank V2 dans `MemoryBrain` |
| `support/gemini_adapter.py` | API externe — reste un service d'appui |
| `support/groq_adapter.py` | API externe — reste un service d'appui |
| `web_interface/app_chat.py` | Interface — inchangée |

### 3.2 Ce qui est nouveau

| Composant V2 | Description |
|---|---|
| `core/neural_router.py` | Superviseur central (remplace la boucle dans `llm_adapter.py`) |
| `core/code_brain.py` | Module coding + auto-amélioration |
| `core/vision_brain.py` | Module multimodal (Qwen-VL) |
| `core/audio_brain.py` | Module STT/TTS |
| `core/interoception_brain.py` | Monitoring interne |
| `core/architecture_graph.py` | Auto-connaissance de LIA |
| `core/self_coding_sandbox.py` | Sandbox d'auto-amélioration |
| `core/self_improvement_evaluator.py` | Évaluateur des auto-modifications |

### 3.3 Changements dans `CoreConfig`

```python
@dataclass
class CoreConfig:
    # === EXISTANT (conservé) ===
    device: str = "auto"
    temperature: float = 0.8
    max_length: int = 15360
    # ...
    
    # === NOUVEAU V2 ===
    
    # Configuration multi-modèles
    router_model: str = "Qwen/Qwen2.5-1.5B-Instruct"           # Superviseur — léger, latence minimale (~4 GB)
    lang_model: str = "Qwen/Qwen2.5-72B-Instruct"              # Communication — qualité maximale (~40 GB VRAM)
    code_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"        # Coding — spécialisé, crucial pour auto-amélioration (~20 GB)
    vision_model: str = "meta-llama/Llama-3.2-11B-Vision-Instruct"  # Vision — bon rapport qualité/VRAM (~22 GB)
    audio_stt_model: str = "openai/whisper-large-v3"            # STT — meilleur open-source multilingue (~3 GB)
    audio_tts_model: str = "hexgrad/Kokoro-82M"                 # TTS — léger, qualité native (~1 GB)
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"     # Embeddings MemoryBrain (~1 GB)
    
    # Activation des modules (pour déploiement progressif)
    enable_code_brain: bool = True
    enable_vision_brain: bool = True
    enable_audio_brain: bool = False  # Phase 2
    enable_self_improvement: bool = False  # Phase 3 (à activer avec précaution)
    
    # Sandbox d'auto-amélioration
    sandbox_timeout_seconds: int = 60
    max_self_modifications_per_session: int = 3
    require_human_approval_for_self_mod: bool = True  # Sécurité
```

---

## 4. Modèles Recommandés sur AMD MI300X

### 4.1 Principe de sélection : "Right model for the right brain"

Avec 192 GB de VRAM, la contrainte n'est plus la taille des modèles mais leur **adéquation au rôle**. La stratégie est simple : modèle léger là où la vitesse prime (routing), modèle de qualité maximale là où la qualité prime (langage, coding).

Aucune obligation de rester sur Qwen — c'est le partenaire du hackathon mais le MI300X peut faire tourner n'importe quel modèle open-source, y compris les plus grands (Llama 3.1 405B tourne sur un seul MI300X selon la documentation AMD).

### 4.2 Sélection des modèles par module

| Module | Modèle retenu | Alternative | VRAM | Justification |
|---|---|---|---|---|
| NeuralRouter | `Qwen2.5-1.5B-Instruct` | `Qwen2.5-3B-Instruct` | ~4 GB | Routing = classification, pas besoin de puissance. Latence minimale prioritaire. |
| LangBrain | `Qwen2.5-72B-Instruct` | `Meta-Llama-3.1-70B-Instruct` | ~40 GB | Voix principale de LIA. Qualité conversationnelle maximale. Le 72B est incomparablement meilleur que le 7B. |
| CodeBrain | `Qwen2.5-Coder-32B-Instruct` | `deepseek-coder-v2-instruct` | ~20 GB | Meilleur modèle de coding open-source disponible. Crucial pour l'auto-amélioration. |
| VisionBrain | `Llama-3.2-Vision-11B` | `Qwen2.5-VL-7B-Instruct` | ~22 GB | Bon rapport qualité/VRAM. Suffisant pour le hackathon. |
| AudioBrain STT | `whisper-large-v3` | `whisper-large-v3-turbo` | ~3 GB | Meilleur STT open-source, excellent multilingue. |
| AudioBrain TTS | `Kokoro-82M` | `Parler-TTS-large` | ~1 GB | Qualité native, open-source, léger. |
| Embeddings | `nomic-embed-text-v1.5` | `all-MiniLM-L6-v2` | ~1 GB | Pour MemoryBrain (recherche sémantique). |
| **Total estimé** | | | **~91 GB** | |
| **VRAM restante** | | | **~101 GB** | Pour contexte long, batch, et marges |

> **Note sur DeepSeek-Coder-V2 :** La version complète fait 236B (MoE). En quantisation INT4, elle tient dans ~60 GB. Si l'auto-amélioration est le cœur du projet, cette option vaut la peine d'être explorée au détriment de VisionBrain.

### 4.3 Comparaison qualitative V1 → V2

| Dimension | V1 (Qwen 7B CPU) | V2 (Multi-modèles MI300X) |
|---|---|---|
| Qualité conversationnelle | Moyenne (7B quantisé 4-bit) | Excellente (72B FP16) |
| Qualité coding | Faible (généraliste 7B) | Excellente (Coder 32B spécialisé) |
| Vitesse d'inférence | ~2-5 tokens/sec (CPU) | ~50-200 tokens/sec (GPU) |
| Multimodal | ❌ Non | ✅ Oui (vision + audio) |
| Contexte max | 32K tokens (limité par RAM) | 128K tokens (Qwen2.5-72B) |
| Auto-amélioration | ❌ Non | ✅ Oui (CodeBrain dédié) |

### 4.4 Stack Technique AMD

```
AMD Instinct MI300X (192 GB HBM3 VRAM)
    └── ROCm 7.2.0
        ├── PyTorch 2.6.0 (backend principal)
        ├── vLLM 0.17.1 (serving multi-modèles en parallèle)
        │   ├── NeuralRouter  → /v1/router   (Qwen2.5-1.5B)
        │   ├── LangBrain     → /v1/lang     (Qwen2.5-72B)
        │   ├── CodeBrain     → /v1/code     (Qwen2.5-Coder-32B)
        │   └── VisionBrain   → /v1/vision   (Llama-3.2-Vision-11B)
        ├── Transformers 4.x (chargement HuggingFace)
        ├── Whisper (AudioBrain STT)
        └── Kokoro / Parler-TTS (AudioBrain TTS)
```

### 4.5 Remplacement de llama-cpp-python

Dans la V1, `llama-cpp-python` était utilisé pour GGUF sur CPU. Sur AMD MI300X, on passe à vLLM + ROCm qui offre une bien meilleure performance et supporte les modèles FP16 complets :

```python
# V1 (CPU, llama-cpp-python, quantisé 4-bit)
from llama_cpp import Llama
model = Llama(
    model_path="models/Qwen2.5-7B-Q4_K_M.gguf",
    n_threads=8,
    n_ctx=32768
)
# Résultat : ~3 tokens/sec, qualité dégradée par quantisation

# V2 (AMD MI300X, vLLM + ROCm, FP16 complet)
from vllm import LLM, SamplingParams

# LangBrain — modèle principal de conversation
lang_brain = LLM(
    model="Qwen/Qwen2.5-72B-Instruct",
    tensor_parallel_size=1,       # 1 GPU MI300X suffit
    dtype="float16",              # FP16 natif sur MI300X
    max_model_len=131072,         # 128K context window
    gpu_memory_utilization=0.40,  # ~40% VRAM = ~77 GB
)

# CodeBrain — modèle spécialisé coding
code_brain = LLM(
    model="Qwen/Qwen2.5-Coder-32B-Instruct",
    dtype="float16",
    max_model_len=32768,
    gpu_memory_utilization=0.20,  # ~20% VRAM = ~38 GB
)

# NeuralRouter — modèle léger pour le routing
router = LLM(
    model="Qwen/Qwen2.5-1.5B-Instruct",
    dtype="float16",
    max_model_len=8192,
    gpu_memory_utilization=0.03,  # ~3% VRAM = ~6 GB
)
# Résultat : ~100-200 tokens/sec, qualité FP16 complète
```

### 4.6 Pourquoi vLLM est idéal pour cette architecture

vLLM gère nativement le **serving multi-modèles en parallèle**, ce qui est exactement ce dont LIA V2 a besoin :

- **PagedAttention** — Gestion efficace de la VRAM pour les longs contextes
- **Continuous batching** — Plusieurs modules peuvent traiter des requêtes simultanément
- **OpenAI-compatible API** — Le NeuralRouter communique avec chaque module via une API unifiée
- **ROCm 7.2 support natif** — Optimisé pour MI300X sans configuration manuelle

---

## 5. Conscience Environnementale Étendue (V2)

Le module `EnvironmentAwareness` existant (`core/environment_awareness.py`) est étendu pour intégrer la conscience multi-modules :

```python
class EnvironmentAwarenessV2(EnvironmentAwareness):
    """
    Extension V2 : LIA est consciente de ses modules actifs,
    de leurs capacités, et de l'état du système AMD.
    """
    
    def get_environment_description(self) -> str:
        """
        Description étendue incluant tous les modules actifs.
        Appelée par LangBrain pour inclure dans le prompt.
        """
        # Existant :
        # • MÉMOIRE : J'ai une mémoire persistante...
        # • GEMINI : J'ai accès à Gemini...
        # • UTILISATEUR : Je peux interagir...
        
        # Nouveau V2 :
        # • CODE : J'ai un module de coding. Je peux générer, analyser et exécuter du code.
        # • VISION : J'ai un module de vision. Je peux analyser des images et des captures d'écran.
        # • AUDIO : J'ai un module audio. Je peux comprendre la voix et parler.
        # • AUTO-AMÉLIORATION : Je peux proposer des modifications de mon propre code.
        # • SANTÉ SYSTÈME : GPU AMD MI300X actif, 56/192 GB VRAM utilisés.
```

---

## 6. Plan de Développement pour le Hackathon (7 jours)

### Priorités pour la soumission

| Jour | Objectif | Module |
|---|---|---|
| 1 | Setup AMD Developer Cloud, SSH, VS Code Remote | Infrastructure |
| 2 | Migrer LangBrain sur vLLM + ROCm (remplacer llama-cpp) | LangBrain |
| 3 | Implémenter NeuralRouter basique (routing texte) | NeuralRouter |
| 4 | Implémenter CodeBrain (Qwen-Coder) + interface | CodeBrain |
| 5 | Implémenter auto-amélioration basique + sandbox | SelfCodingSandbox |
| 6 | Intégrer VisionBrain (Qwen-VL) optionnel | VisionBrain |
| 7 | Démo, vidéo, slides, soumission | Submission |

### Ce qui est faisable en 7 jours (MVP)

- ✅ NeuralRouter + LangBrain + CodeBrain (cœur de l'architecture)
- ✅ Première version de l'auto-amélioration (avec approbation humaine)
- ✅ Migration complète vers vLLM/ROCm sur AMD MI300X
- ✅ Démonstration live de LIA qui s'auto-améliore

### Ce qui est reporté après le hackathon

- AudioBrain (STT/TTS)
- VisionBrain (optionnel pour le hackathon)
- Auto-amélioration sans supervision humaine (nécessite plus de tests)
- ArchitectureGraph complet

---

## 7. Sécurité et Éthique de l'Auto-Amélioration

### 7.1 Principes

1. **Approbation humaine par défaut** — `require_human_approval_for_self_mod = True` dans CoreConfig
2. **Isolation stricte** — Tout nouveau code s'exécute dans un subprocess isolé avant intégration
3. **Rollback automatique** — Si les tests échouent, retour immédiat à la version précédente
4. **IdentityBrain intouchable** — CodeBrain ne peut pas modifier les modules d'identité ou d'éthique
5. **Limite par session** — Maximum 3 auto-modifications par session (`max_self_modifications_per_session`)
6. **Log exhaustif** — Toute auto-modification est tracée dans `ArchitectureGraph.changelog`

### 7.2 Ce que LIA peut et ne peut pas modifier

```
✅ Peut modifier :
   - Paramètres de génération (temperature, max_length)
   - Logique de routing (NeuralRouter patterns)
   - Prompts et templates
   - Stratégies de mémoire (quand et quoi mémoriser)
   - Nouveaux skills (nouvelles fonctions utilitaires)

❌ Ne peut PAS modifier :
   - IdentityBrain (valeurs, éthique, personnalité core)
   - CognitiveSafeguards (limites de sécurité)
   - SelfCodingSandbox (le gardien lui-même)
   - Le mécanisme d'approbation humaine
```

---

## 8. Références

### Code existant utilisé comme base

- `core/llm_adapter.py` — Architecture complète du LLMAdapter V1
- `core/cognitive_planner.py` — Logique de planification (→ NeuralRouter)
- `core/action_executor.py` — Exécution d'actions (→ dispatch)
- `core/pattern_learner.py` — Apprentissage (→ MemoryBrain procédurale)
- `core/self_verifier.py` — Vérification (→ IdentityBrain validator)
- `core/cognitive_safeguards.py` — Garde-fous (→ IdentityBrain + SelfCodingSandbox)
- `memory_service/phrase_memory_processor.py` — MemoryRank V2
- `core/environment_awareness.py` — Conscience environnementale (→ V2 étendue)

### Technologies AMD

- AMD Instinct MI300X — 192 GB VRAM HBM3
- ROCm 7.2.0 — GPU compute stack
- vLLM 0.17.1 — Multi-model serving sur ROCm
- AMD Developer Cloud — Infrastructure cloud

### Modèles Qwen (partenaire hackathon)

- `Qwen/Qwen2.5-1.5B-Instruct` — NeuralRouter (routing léger)
- `Qwen/Qwen2.5-72B-Instruct` — LangBrain (qualité conversationnelle maximale)
- `Qwen/Qwen2.5-Coder-32B-Instruct` — CodeBrain (spécialisé coding + auto-amélioration)
- `meta-llama/Llama-3.2-11B-Vision-Instruct` — VisionBrain

---

*Document de conception LIA V2 — AMD Developer Hackathon 2026*  
*Dernière mise à jour : Mai 2026*
