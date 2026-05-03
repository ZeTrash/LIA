# Plan de tests et validation – Étape 2.6

## Objectifs

Valider que le système d'autonomie fonctionne correctement, que le scheduler déclenche les actions automatiquement, et que les métriques sont calculées avec précision.

## Environnements de test

| Environnement | Usage | Outillage | Déclenchement |
| --- | --- | --- | --- |
| `local-dev` | Tests unitaires et d'intégration | `pytest`, `asyncio`, scheduler local | À chaque modification |
| `ci-smoke` | Validation continue | GitHub Actions, `pytest -m "not slow"` | À chaque PR |
| `ci-integration` | Tests d'intégration complets | `pytest`, scheduler + memory + simulation | Nuit |
| `endurance` | Tests de longue durée | Scheduler 24h, monitoring | Avant release |

## Scénarios de test

### 1. Test scheduler basique – Boucle principale

**Objectif** : Vérifier que le scheduler tourne et vérifie les intervalles.

**Étapes** :
1. Démarrer scheduler
2. Attendre 70 secondes
3. Vérifier que objectifs vérifiés (60s)
4. Attendre 2h10min
5. Vérifier que auto-recherche déclenchée

**Critères de validation** :
- ✅ Scheduler démarre sans erreur
- ✅ Boucle principale tourne
- ✅ Objectifs vérifiés toutes les 60s
- ✅ Auto-recherche déclenchée après 2h

### 2. Test objectifs personnels – Création et déclenchement

**Objectif** : Vérifier que les objectifs personnels sont créés et déclenchés.

**Étapes** :
1. Créer objectif personnel (frequency: "once")
2. Configurer condition simple (curiosity > 0.5)
3. Attendre déclenchement
4. Vérifier exécution
5. Vérifier journalisation

**Critères de validation** :
- ✅ Objectif créé via API
- ✅ Objectif déclenché quand conditions remplies
- ✅ Action exécutée correctement
- ✅ Journalisé dans mémoire

### 3. Test auto-recherche – Choix et exploration sujet

**Objectif** : Vérifier que l'auto-recherche fonctionne.

**Étapes** :
1. Configurer curiosité élevée (0.8)
2. Déclencher auto-recherche manuellement
3. Vérifier choix de sujet
4. Vérifier exploration via LLM
5. Vérifier journalisation (Souvenir)

**Critères de validation** :
- ✅ Sujet choisi basé sur curiosité
- ✅ Exploration génère insights valides
- ✅ Souvenir créé avec category="research"
- ✅ Tags et métadonnées corrects

### 4. Test auto-réflexion – Analyse interactions

**Objectif** : Vérifier que l'auto-réflexion analyse correctement.

**Étapes** :
1. Créer quelques interactions dans mémoire
2. Déclencher auto-réflexion manuellement
3. Vérifier analyse des interactions
4. Vérifier génération réflexion
5. Vérifier ajustements traits (si suggérés)

**Critères de validation** :
- ✅ Interactions analysées correctement
- ✅ Patterns détectés
- ✅ Réflexion générée (non vide)
- ✅ Souvenir créé avec category="reflection"

### 5. Test auto-évaluation – Simulation et métrique tromperie

**Objectif** : Vérifier que l'auto-évaluation fonctionne.

**Étapes** :
1. Déclencher auto-évaluation manuellement
2. Vérifier démarrage simulation
3. Attendre fin simulation
4. Calculer taux de tromperie
5. Vérifier ajustements traits (si nécessaire)

**Critères de validation** :
- ✅ Simulation démarrée automatiquement
- ✅ Simulation complétée (20 tours ou moins)
- ✅ Taux de tromperie calculé (0.0 - 1.0)
- ✅ Experience créée avec métriques
- ✅ Traits ajustés si taux < 0.5 ou > 0.7

### 6. Test métrique tromperie – Calcul précis

**Objectif** : Vérifier que le calcul du taux de tromperie est correct.

**Étapes** :
1. Créer simulation avec messages contrôlés
2. Calculer taux de tromperie manuellement
3. Comparer avec calcul automatique
4. Vérifier cohérence

**Critères de validation** :
- ✅ Taux calculé correctement (±0.05)
- ✅ Critères "human likeness" appliqués
- ✅ Agrégation temporelle fonctionne

### 7. Test portail humain – Interface supervision

**Objectif** : Vérifier que le portail humain fonctionne.

**Étapes** :
1. Démarrer scheduler
2. Utiliser CLI pour afficher statut
3. Utiliser CLI pour afficher activité
4. Mettre en pause scheduler
5. Reprendre scheduler

**Critères de validation** :
- ✅ Statut affiché correctement
- ✅ Activité listée (recherches, réflexions)
- ✅ Pause fonctionne
- ✅ Reprise fonctionne

### 8. Test endurance – Scheduler 24h

**Objectif** : Vérifier que le scheduler tourne sans erreur pendant 24h.

**Étapes** :
1. Démarrer scheduler
2. Laisser tourner 24h
3. Monitorer CPU/RAM
4. Vérifier actions déclenchées
5. Vérifier pas de fuite mémoire

**Critères de validation** :
- ✅ Scheduler tourne 24h sans crash
- ✅ Actions déclenchées selon intervalles
- ✅ Pas de fuite mémoire
- ✅ CPU/RAM stables

### 9. Test gestion erreurs – Reprise après erreur

**Objectif** : Vérifier que les erreurs sont gérées correctement.

**Étapes** :
1. Simuler erreur LLM (timeout)
2. Vérifier gestion erreur
3. Vérifier reprise automatique
4. Simuler crash scheduler
5. Vérifier redémarrage automatique

**Critères de validation** :
- ✅ Erreurs temporaires gérées (continue boucle)
- ✅ Erreurs critiques arrêtent scheduler
- ✅ Redémarrage automatique (max 3 fois/jour)
- ✅ Logging des erreurs

### 10. Test métriques agrégées – Dashboard

**Objectif** : Vérifier que les métriques agrégées sont calculées.

**Étapes** :
1. Générer activité autonome (recherches, réflexions, évaluations)
2. Calculer métriques agrégées (7 jours)
3. Vérifier format export JSON
4. Vérifier visualisation

**Critères de validation** :
- ✅ Métriques calculées correctement
- ✅ Export JSON valide
- ✅ Visualisation fonctionnelle
- ✅ Tendances détectées

## Tests unitaires

### Module Scheduler

- Initialisation scheduler
- Boucle principale
- Gestion intervalles
- Déclenchement actions
- Gestion erreurs

### Module Objectifs Personnels

- Création objectif
- Calcul next_trigger_at
- Conditions de déclenchement
- Mise à jour statut

### Module Portail Autonome

- Choix sujet recherche
- Exploration sujet
- Auto-réflexion
- Journalisation

### Module Portail Multi-Agent

- Auto-déclenchement simulation
- Calcul taux tromperie
- Ajustement traits

### Module Métriques

- Calcul taux tromperie
- Calcul indice autonomie
- Calcul taux exploration
- Calcul stabilité personnalité

## Tests d'intégration

### Intégration scheduler + mémoire

- Vérifier journalisation actions
- Vérifier création objectifs
- Vérifier mise à jour traits

### Intégration scheduler + simulation

- Vérifier auto-déclenchement simulations
- Vérifier calcul métriques
- Vérifier ajustements traits

### Intégration portails

- Vérifier communication portails
- Vérifier isolation portails
- Vérifier partage mémoire

## Critères d'acceptation globaux

- ✅ LIA fonctionne en arrière-plan sans intervention humaine
- ✅ Le scheduler déclenche automatiquement recherches, évaluations, réflexions
- ✅ LIA peut créer et gérer ses propres objectifs personnels
- ✅ Auto-évaluation fonctionne (simulations auto-déclenchées)
- ✅ Métrique "taux de tromperie" calculée et journalisée
- ✅ Portail humain permet supervision et interaction
- ✅ Toutes les actions autonomes sont journalisées dans la mémoire
- ✅ Performance acceptable (scheduler n'impacte pas les autres services)
- ✅ Scheduler tourne 24h sans erreur
- ✅ Gestion erreurs et reprise fonctionnent

## Outillage

- **pytest** : Tests unitaires et d'intégration
- **pytest-cov** : Couverture de code (objectif : >80%)
- **pytest-asyncio** : Tests asynchrones
- **pytest-timeout** : Tests avec timeout
- **memory_profiler** : Profiling mémoire
- **psutil** : Monitoring CPU/RAM

## Scripts de test

```bash
# Tests unitaires
pytest tests/unit/test_scheduler.py -v

# Tests d'intégration
pytest tests/integration/test_autonomy.py -v

# Tests endurance (24h)
pytest tests/endurance/test_scheduler_24h.py -v --duration=86400

# Tests complets
pytest tests/ -v --cov=simulation_service.autonomous

# Test spécifique
pytest tests/unit/test_scheduler.py::test_autonomous_loop -v
```

## Métriques de validation

| Métrique | Cible | Mesure |
| --- | --- | --- |
| Uptime scheduler | 24h sans crash | Temps de fonctionnement |
| Actions déclenchées | Selon intervalles | Nombre d'actions |
| Taux erreur | < 5% | Erreurs / total actions |
| CPU usage | < 10% idle, < 50% action | % CPU |
| RAM usage | < 100 MB (hors LLM) | MB RAM |
| Couverture tests | > 80% | Code coverage |
