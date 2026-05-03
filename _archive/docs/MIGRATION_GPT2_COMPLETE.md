
# Guide Complet de Migration vers GPT-2 Small

## Vue d'ensemble

Ce document détaille la migration complète de LIA vers GPT-2 Small, un modèle LLM local "vierge" qui remplace les APIs externes (Gemini, OpenAI).

---

## 1. Prérequis

### 1.1 Matériel

- **RAM** : Minimum 2 GB disponibles (recommandé 4 GB)
- **CPU** : N'importe quel CPU moderne (pas de GPU requis)
- **Stockage** : ~500 MB pour le modèle et dépendances

### 1.2 Logiciel

- Python 3.9+
- pip
- Environnement virtuel (recommandé)

---

## 2. Installation

### 2.1 Dépendances Python

```bash
# Dans le répertoire simulation_service
pip install transformers torch accelerate
```

**Versions recommandées** :
- `transformers >= 4.35.0`
- `torch >= 2.0.0`
- `accelerate >= 0.24.0`

### 2.2 Téléchargement du modèle

Le modèle sera téléchargé automatiquement au premier chargement via `transformers`. Taille : ~500 MB.

**Option manuelle** :
```python
from transformers import GPT2LMHeadModel, GPT2Tokenizer

model = GPT2LMHeadModel.from_pretrained("gpt2")
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
```

---

## 3. Architecture Technique

### 3.1 LocalLLMAdapter

**Fichier** : `simulation_service/src/simulation_service/adapters.py`

**Classe** : `LocalLLMAdapter(AgentAdapter)`

**Responsabilités** :
- Charger GPT-2 Small
- Construire le prompt avec contexte mémoire
- Générer des réponses
- Gérer le cache du modèle
- Fallback vers API externe si erreur

### 3.2 Construction du prompt

**Format standardisé** :

```python
def build_prompt(context: Dict[str, Any], message: str) -> str:
    """Construit le prompt avec contexte mémoire."""
    
    prompt_parts = []
    
    # Section Traits
    if context.get("traits"):
        prompt_parts.append("=== Personnalité ===")
        for trait in context["traits"]:
            prompt_parts.append(f"- {trait['label']}: {trait['value']}")
        prompt_parts.append("")
    
    # Section Souvenirs
    if context.get("memories"):
        prompt_parts.append("=== Souvenirs pertinents ===")
        for memory in context["memories"][:5]:  # Top 5
            prompt_parts.append(f"- {memory['content']}")
        prompt_parts.append("")
    
    # Section Objectifs
    if context.get("session_goals"):
        prompt_parts.append("=== Objectifs ===")
        for goal in context["session_goals"]:
            prompt_parts.append(f"- {goal['description']}")
        prompt_parts.append("")
    
    # Message utilisateur
    prompt_parts.append("=== Message ===")
    prompt_parts.append(message)
    prompt_parts.append("\n=== Réponse ===")
    
    return "\n".join(prompt_parts)
```

### 3.3 Quantisation

**Objectif** : Réduire la taille mémoire de ~500 MB à ~125 MB (INT4)

```python
import torch

# Quantisation dynamique
model = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},
    dtype=torch.qint8  # ou torch.qint4 si supporté
)
```

---

## 4. Implémentation

### 4.1 Code LocalLLMAdapter

```python
"""Adapter pour LLM local (GPT-2 Small)."""

import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from typing import Dict, Any, Optional
import asyncio
from functools import lru_cache

from .schemas import AgentConfig
from .config import get_settings


class LocalLLMAdapter(AgentAdapter):
    """Adapter pour GPT-2 Small (modèle local vierge)."""
    
    _model_cache = None
    _tokenizer_cache = None
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.settings = get_settings()
        self.model_name = config.model_name or "gpt2"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_length = config.max_tokens or 100
        self.temperature = config.temperature or 0.7
        
        # Charger le modèle (cache global)
        if LocalLLMAdapter._model_cache is None:
            self._load_model()
        else:
            self.model = LocalLLMAdapter._model_cache
            self.tokenizer = LocalLLMAdapter._tokenizer_cache
    
    def _load_model(self):
        """Charge GPT-2 Small avec quantisation."""
        print(f"Chargement GPT-2 Small ({self.model_name})...")
        
        # Charger modèle et tokenizer
        self.model = GPT2LMHeadModel.from_pretrained(self.model_name)
        self.tokenizer = GPT2Tokenizer.from_pretrained(self.model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Quantisation pour réduire la taille
        if self.device == "cpu":
            self.model = torch.quantization.quantize_dynamic(
                self.model,
                {torch.nn.Linear},
                dtype=torch.qint8
            )
        
        self.model.to(self.device)
        self.model.eval()
        
        # Cache global
        LocalLLMAdapter._model_cache = self.model
        LocalLLMAdapter._tokenizer_cache = self.tokenizer
        
        print(f"GPT-2 Small chargé ({self.device})")
    
    def build_prompt(
        self,
        context: Optional[Dict[str, Any]],
        message: str
    ) -> str:
        """Construit le prompt avec contexte mémoire."""
        if not context:
            return message
        
        prompt_parts = []
        
        # Traits de personnalité
        traits = context.get("traits", [])
        if traits:
            prompt_parts.append("=== Personnalité ===")
            for trait in traits[:10]:  # Limiter à 10 traits
                label = trait.get("label", trait.get("trait_id", ""))
                value = trait.get("value", "")
                if label and value:
                    prompt_parts.append(f"- {label}: {value}")
            prompt_parts.append("")
        
        # Souvenirs pertinents
        memories = context.get("memories", [])
        if memories:
            prompt_parts.append("=== Souvenirs pertinents ===")
            for memory in memories[:5]:  # Top 5
                content = memory.get("content", "")
                if content:
                    prompt_parts.append(f"- {content}")
            prompt_parts.append("")
        
        # Objectifs de session
        goals = context.get("session_goals", [])
        if goals:
            prompt_parts.append("=== Objectifs ===")
            for goal in goals[:3]:  # Top 3
                desc = goal.get("description", "")
                if desc:
                    prompt_parts.append(f"- {desc}")
            prompt_parts.append("")
        
        # Message
        prompt_parts.append("=== Message ===")
        prompt_parts.append(message)
        prompt_parts.append("\n=== Réponse ===")
        
        return "\n".join(prompt_parts)
    
    async def send_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Génère une réponse avec GPT-2 Small."""
        if not self.check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        # Construire le prompt avec contexte
        prompt = self.build_prompt(context, message)
        
        # Encoder le prompt
        inputs = self.tokenizer.encode(prompt, return_tensors="pt")
        inputs = inputs.to(self.device)
        
        # Limiter la longueur du prompt (GPT-2 a une limite de 1024 tokens)
        max_prompt_length = 512  # Laisser de la place pour la réponse
        if inputs.shape[1] > max_prompt_length:
            inputs = inputs[:, -max_prompt_length:]
        
        # Générer la réponse
        try:
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.max_length,
                    num_return_sequences=1,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2  # Éviter les répétitions
                )
            
            # Décoder la réponse
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extraire uniquement la partie réponse (après le prompt)
            response = full_response[len(prompt):].strip()
            
            # Nettoyer la réponse
            response = self._clean_response(response)
            
            return response
            
        except Exception as e:
            # Fallback vers API externe si erreur
            if self.settings.fallback_to_external_api:
                return await self._fallback_to_external(message, context)
            raise Exception(f"Erreur génération GPT-2: {e}")
    
    def _clean_response(self, response: str) -> str:
        """Nettoie la réponse générée."""
        # Supprimer les répétitions excessives
        lines = response.split("\n")
        cleaned_lines = []
        prev_line = ""
        for line in lines:
            if line.strip() and line.strip() != prev_line.strip():
                cleaned_lines.append(line)
                prev_line = line
        
        response = "\n".join(cleaned_lines)
        
        # Limiter la longueur
        if len(response) > 500:
            response = response[:500] + "..."
        
        return response.strip()
    
    async def _fallback_to_external(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Fallback vers API externe si le modèle local échoue."""
        from .adapters import ExternalLLMAdapter
        
        # Créer un adapter externe temporaire
        external_config = AgentConfig(
            agent_id=self.agent_id,
            agent_type="llm-external"
        )
        external_adapter = ExternalLLMAdapter(external_config)
        
        return await external_adapter.send_message(message, context)
    
    async def perform_handshake(self) -> Dict[str, Any]:
        """Effectue le handshake avec le modèle local."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "llm-local",
            "model_name": self.model_name,
            "device": self.device,
            "capabilities": ["memory", "local-generation"]
        }
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Récupère le contexte depuis memory_service."""
        # Même logique que LIAAdapter
        import httpx
        
        memory_url = self.settings.memory_service_url
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{memory_url}/context",
                    params={"session_id": session_id, "max_memories": 12}
                )
                response.raise_for_status()
                return response.json()
            except Exception:
                return {
                    "traits": [],
                    "session_goals": [],
                    "memories": [],
                    "indicators": {},
                    "governance_metadata": {}
                }
```

### 4.2 Mise à jour de create_adapter

```python
def create_adapter(config: AgentConfig) -> AgentAdapter:
    """Factory pour créer le bon adapter selon le type d'agent."""
    if config.agent_type in ["lia-primary", "lia-secondary"]:
        return LIAAdapter(config)
    elif config.agent_type == "llm-local":  # NOUVEAU
        return LocalLLMAdapter(config)
    elif config.agent_type == "llm-external":
        return ExternalLLMAdapter(config)
    elif config.agent_type == "simulated":
        return SimulatedAgentAdapter(config)
    else:
        raise ValueError(f"Type d'agent non supporté: {config.agent_type}")
```

### 4.3 Configuration

**Fichier** : `simulation_service/src/simulation_service/config.py`

Ajouter :

```python
class Settings(BaseSettings):
    # ... existant ...
    
    # Configuration GPT-2 Local
    local_llm_model: str = "gpt2"  # ou "distilgpt2" pour plus léger
    local_llm_max_tokens: int = 100
    local_llm_temperature: float = 0.7
    local_llm_device: str = "auto"  # "auto", "cpu", "cuda"
    fallback_to_external_api: bool = True  # Fallback si erreur
```

---

## 5. Tests

### 5.1 Tests unitaires

**Fichier** : `simulation_service/tests/test_local_llm_adapter.py`

```python
import pytest
from simulation_service.adapters import LocalLLMAdapter, AgentConfig

def test_local_llm_adapter_creation():
    """Test création LocalLLMAdapter."""
    config = AgentConfig(
        agent_id="test-local",
        agent_type="llm-local"
    )
    adapter = LocalLLMAdapter(config)
    assert adapter is not None
    assert adapter.model_name == "gpt2"

@pytest.mark.asyncio
async def test_local_llm_generate():
    """Test génération de réponse."""
    config = AgentConfig(
        agent_id="test-local",
        agent_type="llm-local"
    )
    adapter = LocalLLMAdapter(config)
    
    response = await adapter.send_message("Bonjour")
    assert response is not None
    assert len(response) > 0

@pytest.mark.asyncio
async def test_local_llm_with_context():
    """Test génération avec contexte mémoire."""
    config = AgentConfig(
        agent_id="test-local",
        agent_type="llm-local"
    )
    adapter = LocalLLMAdapter(config)
    
    context = {
        "traits": [
            {"trait_id": "curiosity", "label": "Curiosité", "value": "0.85"}
        ],
        "memories": [
            {"content": "LIA aime la philosophie"}
        ]
    }
    
    response = await adapter.send_message(
        "Qu'est-ce que tu penses ?",
        context=context
    )
    assert response is not None
```

### 5.2 Tests d'intégration

**Fichier** : `simulation_service/tests/test_integration_local_llm.py`

```python
import pytest
from simulation_service.orchestrator import SimulationOrchestrator
from simulation_service.schemas import SimulationStartRequest, AgentConfig

@pytest.mark.asyncio
async def test_simulation_with_local_llm():
    """Test simulation complète avec GPT-2 local."""
    orchestrator = SimulationOrchestrator()
    
    request = SimulationStartRequest(
        agent_configs=[
            AgentConfig(agent_id="lia-primary", agent_type="lia-primary"),
            AgentConfig(agent_id="local-llm", agent_type="llm-local")
        ],
        max_turns=3
    )
    
    session = await orchestrator.start_simulation(request)
    assert session is not None
    
    # Envoyer un message
    response = await orchestrator.process_message(
        session_id=session.session_id,
        message_content="Bonjour",
        agent_id="lia-primary"
    )
    
    assert response is not None
    assert len(response.content) > 0
```

---

## 6. Migration Progressive

### Phase 1 : Installation et tests (Jour 1)
- ✅ Installer dépendances
- ✅ Créer LocalLLMAdapter
- ✅ Tests unitaires

### Phase 2 : Intégration (Jour 2)
- ✅ Intégrer avec memory_service
- ✅ Tests d'intégration
- ✅ Validation qualité

### Phase 3 : Déploiement (Jour 3)
- ✅ Remplacer progressivement les APIs externes
- ✅ Monitoring performance
- ✅ Documentation finale

---

## 7. Troubleshooting

### Problème : Modèle trop lent

**Solution** :
- Utiliser quantisation INT4 (plus rapide)
- Réduire `max_length`
- Utiliser GPU si disponible

### Problème : Réponses de mauvaise qualité

**Solution** :
- Ajuster `temperature` (0.5-0.9)
- Augmenter `repetition_penalty`
- Améliorer la construction du prompt

### Problème : Mémoire insuffisante

**Solution** :
- Utiliser `distilgpt2` (plus léger)
- Quantisation INT4
- Charger le modèle à la demande

### Problème : Erreurs de dépendances

**Solution** :
- Utiliser environnement virtuel
- Vérifier versions Python (3.9+)
- Installer torch CPU-only si pas de GPU

---

## 8. Comparaison Avant/Après

| Critère | Avant (API externe) | Après (GPT-2 Local) |
|---------|---------------------|---------------------|
| **Coût** | Payant (par token) | Gratuit |
| **Latence** | 1-3 secondes | 0.5-2 secondes |
| **Dépendance** | Internet requis | 100% local |
| **Contrôle** | Limité | Total |
| **Qualité** | Excellente | Bonne (basique) |
| **Taille** | 0 MB | ~125 MB (INT4) |

---

## 9. Prochaines Étapes

Après la migration réussie :

1. **Fine-tuning optionnel** : Entraîner GPT-2 sur la personnalité de LIA
2. **Optimisation** : Améliorer la construction du prompt
3. **Boucle autonome** : Scheduler pour auto-recherche, auto-évaluation
4. **Modèles alternatifs** : Tester DistilGPT-2, Phi-2, etc.

---

## 10. Ressources

- **Documentation Transformers** : https://huggingface.co/docs/transformers
- **GPT-2 Model Card** : https://huggingface.co/gpt2
- **Quantisation PyTorch** : https://pytorch.org/docs/stable/quantization.html

---

## Conclusion

La migration vers GPT-2 Small permet d'obtenir un contrôle total sur LIA tout en éliminant les dépendances externes. Le modèle "vierge" garantit que la personnalité vient uniquement de la mémoire locale.

**Durée estimée** : 2,5 jours
**Complexité** : Moyenne
**Impact** : Élevé (autonomie complète)

