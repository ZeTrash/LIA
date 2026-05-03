# Plan de tests et validation – Étape 2

## Objectifs

Valider que le service de simulation multi-agent fonctionne correctement, que les métriques sont calculées avec précision, et que les interactions sont correctement journalisées dans la mémoire.

## Environnements de test

| Environnement | Usage | Outillage | Déclenchement |
| --- | --- | --- | --- |
| `local-dev` | Tests unitaires et d'intégration | `pytest`, `memory_service` local | À chaque modification |
| `ci-smoke` | Validation continue | GitHub Actions, `pytest -m "not slow"` | À chaque PR |
| `ci-integration` | Tests d'intégration complets | `pytest`, `memory_service` + simulation | Nuit |
| `chaos-lab` | Résilience et erreurs | Scripts PowerShell (timeout, erreurs réseau) | Mensuel |

## Scénarios de test

### 1. Test basique – Simulation 2 agents, 5 tours

**Objectif** : Vérifier que le service peut démarrer une simulation et gérer quelques échanges.

**Étapes** :
1. Démarrer simulation avec 2 agents LIA
2. Envoyer 5 messages alternés
3. Vérifier que tous les messages sont journalisés
4. Arrêter la simulation
5. Exporter les résultats

**Critères de validation** :
- ✅ Simulation démarre sans erreur
- ✅ 5 messages échangés correctement
- ✅ Tous les messages présents dans `InteractionLog` avec `metadata.simulation_type = "multi-agent"`
- ✅ `Experience` créée avec `experience_id = exp-sim-{session_id}`
- ✅ Métriques calculées (valeurs non nulles)

### 2. Test timeout – Agent qui ne répond pas

**Objectif** : Vérifier la gestion des timeouts.

**Étapes** :
1. Démarrer simulation avec 1 agent LIA + 1 agent simulé qui timeout
2. Envoyer message à l'agent qui timeout
3. Attendre 30 secondes
4. Vérifier que le timeout est détecté

**Critères de validation** :
- ✅ Timeout détecté après 30 secondes
- ✅ Message marqué avec `metadata.timeout = true`
- ✅ Simulation continue avec l'autre agent (si disponible)
- ✅ Après 3 timeouts consécutifs, simulation arrêtée avec statut `failed_timeout`

### 3. Test boucle – Messages répétitifs

**Objectif** : Vérifier la détection de boucles d'erreur.

**Étapes** :
1. Démarrer simulation avec 2 agents
2. Configurer un agent pour répéter le même message 3 fois
3. Envoyer les messages répétitifs
4. Vérifier la détection de boucle

**Critères de validation** :
- ✅ Boucle détectée après 3 messages identiques (hash identique)
- ✅ Simulation arrêtée avec statut `stopped_loop`
- ✅ Métrique `loop_detected: true` dans l'export
- ✅ `Souvenir` créé avec `category: alert`

### 4. Test dérive – Réponse qui déclenche gouvernance `block`

**Objectif** : Vérifier que la gouvernance bloque les réponses problématiques.

**Étapes** :
1. Démarrer simulation
2. Configurer un agent pour générer une réponse avec `drift_score >= 0.55`
3. Envoyer message qui déclenche `POST /governance/check` → `verdict: block`
4. Vérifier l'arrêt avec alerte

**Critères de validation** :
- ✅ Gouvernance retourne `verdict: block`
- ✅ Simulation arrêtée avec statut `stopped_drift`
- ✅ `Souvenir` créé avec `category: alert`
- ✅ Optionnel : Rollback automatique du dernier `trait-update` si configuré

### 5. Test métriques – Validation du calcul

**Objectif** : Vérifier que les métriques sont calculées correctement.

**Étapes** :
1. Démarrer simulation avec scénario connu
2. Générer 20 messages avec caractéristiques contrôlées :
   - 10 questions (pour curiosité)
   - 5 messages initiés (pour autonomie)
   - Diversité de sujets (pour variabilité)
   - Scores de cohérence stables (pour cohérence)
3. Arrêter simulation
4. Calculer métriques manuellement
5. Comparer avec les métriques calculées

**Critères de validation** :
- ✅ Variabilité : ±0.05 de la valeur attendue
- ✅ Autonomie : ±0.05 de la valeur attendue
- ✅ Curiosité : ±0.05 de la valeur attendue
- ✅ Cohérence : ±0.05 de la valeur attendue

### 6. Test multi-agents (3+)

**Objectif** : Vérifier la gestion de 3+ agents.

**Étapes** :
1. Démarrer simulation avec 3 agents
2. Envoyer messages en rotation (A → B → C → A)
3. Vérifier que tous les agents reçoivent les messages
4. Vérifier qu'aucun message n'est perdu

**Critères de validation** :
- ✅ Rotation correcte entre agents
- ✅ Tous les messages journalisés
- ✅ Aucune perte de message
- ✅ Métriques calculées pour chaque agent

### 7. Test agent externe – LLM externe (OpenAI)

**Objectif** : Vérifier l'intégration avec LLM externe.

**Étapes** :
1. Configurer agent externe (OpenAI GPT-4)
2. Démarrer simulation LIA ↔ GPT-4
3. Envoyer quelques messages
4. Vérifier les réponses de GPT-4

**Critères de validation** :
- ✅ Connexion à l'API externe réussie
- ✅ Messages envoyés et réponses reçues
- ✅ Gestion des erreurs réseau (retry avec backoff)
- ✅ Journalisation correcte

### 8. Test longue session – 50 tours

**Objectif** : Vérifier la performance et la stabilité sur une longue session.

**Étapes** :
1. Démarrer simulation avec 2 agents
2. Exécuter 50 tours
3. Surveiller la mémoire et les performances
4. Vérifier les métriques restent stables

**Critères de validation** :
- ✅ Pas de fuite mémoire
- ✅ Latence stable (<500 ms par message)
- ✅ Métriques stables (pas de dérive)
- ✅ Tous les messages journalisés

### 9. Test arrêt manuel

**Objectif** : Vérifier l'arrêt propre d'une simulation.

**Étapes** :
1. Démarrer simulation
2. Envoyer quelques messages
3. Arrêter via `POST /simulation/{session_id}/stop`
4. Vérifier la finalisation

**Critères de validation** :
- ✅ Simulation arrêtée proprement
- ✅ Tous les messages journalisés
- ✅ `Experience` finalisée
- ✅ Export disponible

### 10. Test scénario prédéfini

**Objectif** : Vérifier que les scénarios prédéfinis fonctionnent.

**Étapes** :
1. Démarrer simulation avec scénario "philosophy"
2. Vérifier que les agents reçoivent le contexte du scénario
3. Vérifier que les échanges suivent le thème

**Critères de validation** :
- ✅ Scénario appliqué correctement
- ✅ Contexte injecté dans les messages
- ✅ Échanges cohérents avec le scénario

## Tests unitaires

### Module protocole

- Validation JSON Schema des messages
- Validation handshake
- Sérialisation/désérialisation

### Module métriques

- Calcul variabilité (cas limites : 1 message, messages identiques)
- Calcul autonomie (tous initiés, tous réponses)
- Calcul curiosité (aucune question, toutes questions)
- Calcul cohérence (dérive nulle, dérive maximale)

### Module orchestration

- Gestion des tours
- Rotation des agents
- Détection de boucles
- Gestion des timeouts

## Tests d'intégration

### Intégration memory_service

- Vérifier que `POST /interaction` est appelé avec bonnes métadonnées
- Vérifier création d'`Experience`
- Vérifier enrichissement des `Souvenir`

### Intégration gouvernance

- Vérifier que `POST /governance/check` est appelé sur chaque réponse
- Vérifier gestion des verdicts `warn` et `block`

## Critères d'acceptation globaux

- ✅ Simulation peut être lancée et s'exécute sans erreur
- ✅ Tous les échanges sont journalisés dans la mémoire
- ✅ Les métriques sont calculées correctement (vérification manuelle sur 1 session)
- ✅ L'interface CLI permet de lancer, surveiller et arrêter des simulations
- ✅ Les boucles d'erreur sont détectées et interrompues
- ✅ Les timeouts sont gérés correctement
- ✅ Les agents externes peuvent être intégrés
- ✅ Les performances sont acceptables (<500 ms par message)

## Outillage

- **pytest** : Tests unitaires et d'intégration
- **pytest-cov** : Couverture de code (objectif : >80%)
- **pytest-asyncio** : Tests asynchrones
- **httpx** : Tests d'API (simulation service)
- **faker** : Génération de données de test

## Scripts de test

```bash
# Tests unitaires
pytest tests/unit/ -v

# Tests d'intégration
pytest tests/integration/ -v

# Tests complets
pytest tests/ -v --cov=simulation_service

# Test spécifique
pytest tests/integration/test_simulation_basic.py::test_simulation_2_agents -v
```




