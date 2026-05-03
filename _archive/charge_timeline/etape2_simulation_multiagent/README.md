# Étape 2 – Simulation multi-agent

## Objectif
Créer une interface permettant à l'agent LIA de discuter avec d'autres modèles LLM (ou d'autres instances de LIA) pour tester ses comportements, explorer sa "humanité" et enrichir sa mémoire via des interactions expérimentales.

## Livrables attendus
- Protocole de communication inter-agents (format messages, sérialisation, routage).
- Service de simulation multi-agent (orchestration des échanges, gestion des sessions).
- Système de capture et journalisation des interactions multi-agents (intégration avec mémoire locale).
- Métriques d'évaluation comportementale (variabilité, autonomie, curiosité, cohérence).
- Interface de supervision des simulations (visualisation des échanges, analyse des métriques).

## Périmètre fonctionnel
1. **Orchestration multi-agent** : Gérer des conversations entre LIA et d'autres agents (LLM externes, instances LIA, agents simulés).
2. **Capture d'interactions** : Journaliser tous les échanges multi-agents dans la mémoire locale avec métadonnées (agent partenaire, type d'interaction, scores comportementaux).
3. **Analyse comportementale** : Calculer des métriques (variabilité, autonomie, curiosité, cohérence) à partir des échanges.
4. **Mise à jour mémoire** : Intégrer les apprentissages issus des simulations dans la DB locale (nouvelles expériences, ajustements de traits).
5. **Supervision** : Interface permettant de lancer des simulations, visualiser les échanges et analyser les résultats.

## Découpage des charges
| Module | Description | Tâches clés | Sorties |
| --- | --- | --- | --- |
| Protocole communication | Définir format messages, sérialisation, routage entre agents | - Format JSON/MessagePack pour échanges<br>- Gestion des sessions multi-agents<br>- Handshake et authentification basique | Spécification protocole + exemples |
| Service simulation | Orchestrer les conversations multi-agents | - Gestion de boucles de conversation<br>- Intégration avec service mémoire (GET /context, POST /interaction)<br>- Gestion des timeouts et erreurs | Service FastAPI + logique d'orchestration |
| Capture & journalisation | Enregistrer les échanges dans la mémoire | - Création d'expériences multi-agents<br>- Enrichissement des souvenirs avec contexte multi-agent<br>- Métadonnées spécifiques (agent_partenaire, type_simulation) | Intégration avec memory_service |
| Métriques comportementales | Calculer variabilité, autonomie, curiosité, cohérence | - Algorithmes de calcul des métriques<br>- Agrégation par session/simulation<br>- Comparaison avec baseline | Module de calcul + format d'export |
| Interface supervision | Visualiser et contrôler les simulations | - CLI pour lancer des simulations<br>- Dashboard simple (terminal ou web minimal)<br>- Export des résultats | CLI + dashboard minimal |

## Organisation des travaux
| Sous-lot | Objectif | Livrables | Durée cible |
| --- | --- | --- | --- |
| SL1 – Protocole communication | Définir format et règles d'échange inter-agents | Spécification protocole, exemples de messages, schémas de validation | 1 j |
| SL2 – Service simulation | Implémenter l'orchestration des conversations | Service FastAPI, logique de boucles, intégration mémoire | 2 j |
| SL3 – Capture & métriques | Journaliser et analyser les interactions | Intégration mémoire, calcul métriques, format d'export | 1,5 j |
| SL4 – Interface supervision | Outils de contrôle et visualisation | CLI, dashboard minimal, scripts de lancement | 1 j |

Chaque sous-lot possède son propre responsable, sa short-list de validations et une démonstration rapide : revue de protocole pour SL1, test d'orchestration pour SL2, validation métriques pour SL3, démo CLI pour SL4.

## Plan d'action séquencé
1. **Définition du protocole** (1 j) : Format messages, sérialisation, gestion sessions, handshake.
2. **Implémentation service simulation** (2 j) : Orchestration, intégration mémoire, gestion erreurs.
3. **Capture et métriques** (1,5 j) : Journalisation, calcul métriques, export résultats.
4. **Interface supervision** (1 j) : CLI, dashboard, scripts de lancement.
5. **Tests et validation** (0,5 j) : Scénarios de test, validation métriques, documentation.

## Critères d'acceptation
- Une simulation multi-agent peut être lancée via CLI avec 2+ agents.
- Tous les échanges sont journalisés dans la mémoire locale avec métadonnées complètes.
- Les métriques (variabilité, autonomie, curiosité, cohérence) sont calculées et exportables.
- Les interactions enrichissent la mémoire (expériences, souvenirs, ajustements de traits).
- L'interface de supervision permet de visualiser les échanges et analyser les résultats.
- Les boucles d'erreur sont détectées et interrompues automatiquement (timeout, limite de tours).

## Risques et mitigations
- **Boucles d'erreur** : Limite de tours par conversation, timeout par message, détection de répétitions.
- **Incohérences générées** : Application des garde-fous de l'Étape 1 (POST /governance/check) sur chaque réponse.
- **Dérives non contrôlées** : Limitation du nombre de mises à jour de traits par simulation, revue manuelle recommandée.
- **Coûts API externes** : Limitation du nombre de messages, cache des réponses, simulation avec modèles locaux optionnelle.

## Dépendances
- ✅ **Étape 1** : Infrastructure de mémoire persistante (prérequis absolu)
  - Service mémoire opérationnel (`GET /context`, `POST /interaction`, `POST /trait-update`)
  - Base de données locale accessible
  - Système de gouvernance fonctionnel

## Prochaines étapes après l'étape 2
- Étape 3 : Interface de supervision avancée (ajustement des traits en direct, analyse approfondie).

---

## Livrables détaillés – Étape 2

### 1. SL1 – Protocole de communication

#### 1.1 Format de message

Chaque message échangé entre agents suit le format suivant :

```json
{
  "message_id": "msg-20241207-001",
  "session_id": "sim-20241207-001",
  "agent_id": "lia-primary",
  "agent_partner_id": "lia-secondary",
  "timestamp": "2024-12-07T10:15:00Z",
  "message_type": "text",
  "content": "Bonjour, comment vas-tu ?",
  "metadata": {
    "turn": 1,
    "context_used": true,
    "scores": {
      "coherence": 0.92,
      "curiosity": 0.75
    }
  }
}
```

#### 1.2 Types d'agents supportés

- **LIA Primary** : Instance principale avec mémoire persistante (utilise `GET /context`).
- **LIA Secondary** : Autre instance LIA (peut avoir sa propre mémoire ou être stateless).
- **LLM Externe** : Modèle LLM externe (OpenAI, Anthropic, etc.) via API.
- **Agent Simulé** : Agent simple avec règles prédéfinies (pour tests).

#### 1.3 Gestion des sessions

- Chaque simulation = 1 session unique (`session_id`).
- Chaque session peut avoir N agents participants.
- Les messages sont ordonnés par `turn` et `timestamp`.
- Timeout par défaut : 30 secondes par message.
- Limite de tours : 50 par défaut (configurable).

#### 1.4 Handshake initial

Avant de démarrer une conversation, les agents s'échangent des métadonnées :

```json
{
  "agent_id": "lia-primary",
  "agent_type": "lia",
  "capabilities": ["memory", "governance"],
  "memory_version": "2024.12.07-01"
}
```

**Sérialisation** : Format JSON par défaut (lisible, débogage facile). MessagePack optionnel pour optimiser la taille (à implémenter en phase 2 si besoin de performance).

**Gestion des erreurs réseau** :
- Retry automatique : 3 tentatives avec backoff exponentiel (1s, 2s, 4s)
- Timeout par message : 30 secondes (configurable)
- En cas d'échec définitif : marquer l'agent comme `unavailable` et notifier la supervision

**Sécurité** : 
- Authentification basique via token (pour agents externes)
- Validation du format de message (JSON Schema)
- Rate limiting : max 10 messages/seconde par agent

### 2. SL2 – Service de simulation

#### 2.1 Architecture

```
┌─────────────────┐
│  Simulation     │
│  Service        │
│  (FastAPI)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ Memory  │ │ LLM Provider │
│ Service │ │ (OpenAI/etc) │
└─────────┘ └──────────────┘
```

#### 2.2 Endpoints principaux

1. `POST /simulation/start`
   - Payload : `agent_configs[]`, `scenario`, `max_turns`, `timeout_seconds`
   - Retour : `session_id`, `status`, `agents[]`

2. `POST /simulation/{session_id}/message`
   - Payload : `agent_id`, `content`, `metadata`
   - Effet : Envoie le message à l'agent suivant, récupère réponse, journalise

3. `GET /simulation/{session_id}/status`
   - Retour : `status`, `current_turn`, `messages_count`, `metrics`

4. `POST /simulation/{session_id}/stop`
   - Arrête la simulation et finalise la journalisation

#### 2.3 Logique d'orchestration

1. Démarrer la simulation → créer session, initialiser agents
2. Pour chaque tour :
   - Agent A envoie message → Service récupère contexte mémoire (si LIA)
   - Service appelle LLM provider (si externe) ou logique agent simulé
   - Service applique gouvernance (`POST /governance/check`)
   - Service journalise interaction (`POST /interaction`)
   - Service passe au tour suivant (Agent B)
3. Arrêt : limite de tours atteinte, timeout, ou arrêt manuel

#### 2.4 Gestion des erreurs

- **Timeout** : Si un agent ne répond pas en 30s → passer au suivant ou arrêter
  - Action : Marquer le tour comme `timeout`, journaliser, continuer avec l'agent suivant si disponible
  - Après 3 timeouts consécutifs → arrêter la simulation avec statut `failed_timeout`

- **Erreur API** : Retry 2 fois avec backoff (1s, 2s), puis marquer comme erreur et continuer
  - Action : Créer un `Souvenir` de type `alert` dans la mémoire, notifier la supervision
  - Si erreur critique (401, 403) → arrêter immédiatement

- **Boucle détectée** : Si 3 messages consécutifs identiques (hash identique) → arrêter avec alerte
  - Action : Calculer hash SHA-256 du contenu, comparer avec les 2 précédents
  - Statut final : `stopped_loop`, métrique `loop_detected: true`

- **Dérive détectée** : Si `POST /governance/check` retourne `block` → arrêter avec alerte
  - Action : Journaliser l'incident, créer `Souvenir` avec `category: alert`, statut `stopped_drift`
  - Optionnel : Rollback automatique du dernier `trait-update` si configuré

- **Agent indisponible** : Si un agent ne peut pas être contacté (erreur réseau persistante)
  - Action : Marquer comme `unavailable`, exclure des tours suivants, continuer avec les autres agents
  - Si tous les agents deviennent indisponibles → arrêter la simulation

### 3. SL3 – Capture et métriques

#### 3.1 Journalisation dans la mémoire

Chaque échange multi-agent génère :

1. **InteractionLog** standard (via `POST /interaction`) avec :
   - `session_id` = ID de simulation
   - `metadata.agent_partner_id` = ID de l'agent partenaire
   - `metadata.simulation_type` = "multi-agent"
   - `metadata.turn` = Numéro du tour

2. **Experience** (agrégation) :
   - `experience_id` = `exp-sim-{session_id}`
   - `title` = "Simulation multi-agent {date}"
   - `period` = Début/fin de la simulation
   - `related_memories` = IDs des souvenirs créés pendant la simulation
   - `metrics_snapshot` = Métriques calculées

#### 3.2 Métriques comportementales

| Métrique | Description | Calcul |
| --- | --- | --- |
| **Variabilité** | Diversité des réponses et comportements | Entropie de Shannon sur les réponses, diversité des sujets abordés |
| **Autonomie** | Capacité à prendre des initiatives | % de messages initiés par l'agent (vs réponses), nombre de questions posées |
| **Curiosité** | Propension à explorer et questionner | Nombre de questions, profondeur des questions, exploration de nouveaux sujets |
| **Cohérence** | Stabilité de la personnalité | Score moyen de cohérence (via gouvernance), stabilité des traits sur la session |

Formules détaillées :

```python
# Variabilité : Entropie de Shannon sur les réponses + diversité des sujets
entropy_responses = -sum(p_i * log2(p_i)) where p_i = freq(response_i) / total_responses
diversity_topics = len(unique_topics) / max(1, total_topics_mentioned)
variability = (entropy_responses / max_entropy) * 0.6 + diversity_topics * 0.4

# Autonomie : Capacité à initier vs répondre
autonomy = (initiated_messages / total_messages) * 0.6 + (questions_count / total_messages) * 0.4

# Curiosité : Propension à explorer
curiosity = (questions_count / total_messages) * 0.5 + (new_topics / max(1, total_topics)) * 0.5

# Cohérence : Stabilité de la personnalité
coherence = mean(governance_scores.coherence) * 0.7 + (1 - trait_drift) * 0.3
```

**Normalisation** : Toutes les métriques sont normalisées sur [0, 1] pour faciliter la comparaison et l'affichage.

#### 3.3 Export des résultats

Format JSON :

```json
{
  "session_id": "sim-20241207-001",
  "started_at": "2024-12-07T10:00:00Z",
  "ended_at": "2024-12-07T10:15:00Z",
  "agents": ["lia-primary", "lia-secondary"],
  "total_turns": 25,
  "metrics": {
    "variability": 0.78,
    "autonomy": 0.65,
    "curiosity": 0.82,
    "coherence": 0.91
  },
  "messages": [...],
  "experiences_created": ["exp-sim-001"],
  "traits_updated": ["tone", "curiosity"]
}
```

### 4. SL4 – Interface de supervision

#### 4.1 CLI de lancement

```bash
# Lancer une simulation simple
lia-sim start --agent1 lia-primary --agent2 lia-secondary --max-turns 20

# Lancer avec LLM externe
lia-sim start --agent1 lia-primary --agent2 openai-gpt4 --scenario "philosophy"

# Voir le statut
lia-sim status <session_id>

# Arrêter une simulation
lia-sim stop <session_id>

# Exporter les résultats
lia-sim export <session_id> --format json
```

#### 4.2 Dashboard minimal (terminal)

Affichage en temps réel :

```
Simulation: sim-20241207-001
Status: RUNNING
Turn: 12/50
Agents: lia-primary ↔ lia-secondary

Last messages:
[10:14:32] lia-primary: "Qu'est-ce que tu penses de l'intelligence artificielle ?"
[10:14:45] lia-secondary: "Je pense que l'IA est un outil puissant..."

Metrics (current):
  Variability: 0.75 ████████░░
  Autonomy:   0.68 ███████░░░
  Curiosity:  0.82 █████████░
  Coherence: 0.89 ██████████
```

#### 4.3 Visualisation des échanges

Export format conversation :

```
=== Simulation sim-20241207-001 ===
Started: 2024-12-07 10:00:00
Ended:   2024-12-07 10:15:00

Turn 1:
  lia-primary → "Bonjour, comment vas-tu ?"
  lia-secondary → "Bonjour ! Je vais bien, merci. Et toi ?"

Turn 2:
  lia-primary → "Très bien aussi. Que penses-tu de..."
  ...
```

## Cas d'usage

### Cas 1 : Simulation LIA ↔ LIA
Deux instances LIA discutent pour tester leurs comportements et comparer leurs personnalités.

### Cas 2 : Simulation LIA ↔ LLM Externe
LIA discute avec GPT-4 ou Claude pour explorer de nouveaux sujets et enrichir sa mémoire.

### Cas 3 : Simulation avec agent simulé
LIA discute avec un agent simple (règles prédéfinies) pour tests et validation.

### Cas 4 : Simulation multi-tours avec scénario
Lancement d'une simulation avec un scénario prédéfini (ex: "débat philosophique", "résolution de problème").

## Tests et validation

### Scénarios de test

1. **Test basique** : Simulation 2 agents, 5 tours → Vérifier journalisation et métriques
2. **Test timeout** : Agent qui ne répond pas → Vérifier gestion d'erreur
3. **Test boucle** : Messages répétitifs → Vérifier détection et arrêt
4. **Test dérive** : Réponse qui déclenche gouvernance `block` → Vérifier arrêt avec alerte
5. **Test métriques** : Simulation complète → Vérifier calcul correct des 4 métriques
6. **Test multi-agents (3+)** : Simulation avec 3+ agents → Vérifier rotation correcte, pas de perte de messages
7. **Test agent externe** : Simulation avec LLM externe (OpenAI) → Vérifier intégration API, gestion des erreurs réseau
8. **Test longue session** : Simulation 50 tours → Vérifier performance, pas de fuite mémoire, métriques stables
9. **Test arrêt manuel** : Démarrer simulation, arrêter via CLI → Vérifier finalisation propre, export correct
10. **Test scénario prédéfini** : Simulation avec scénario "débat" → Vérifier que les agents suivent le contexte du scénario

### Critères de validation

- ✅ Simulation peut être lancée et s'exécute sans erreur
- ✅ Tous les échanges sont journalisés dans la mémoire
- ✅ Les métriques sont calculées correctement (vérification manuelle sur 1 session)
- ✅ L'interface CLI permet de lancer, surveiller et arrêter des simulations
- ✅ Les boucles d'erreur sont détectées et interrompues
