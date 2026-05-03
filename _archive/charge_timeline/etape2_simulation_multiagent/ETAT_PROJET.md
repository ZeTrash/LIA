# État du projet - Étape 2 : Simulation multi-agent

**Date** : 2024-12-07  
**Statut global** : 🟡 **En cours de définition**

---

## 📋 RÉSUMÉ EXÉCUTIF

L'Étape 2 est actuellement au stade de **définition et planification**. Le cahier des charges détaillé a été créé, mais **aucun code n'a encore été implémenté**.

**Prérequis** : ✅ **Étape 1 complétée** (91% de conformité, prêt pour production)

---

## ✅ CE QUI EST FAIT

### 1. Documentation

- ✅ **Cahier des charges complet** (`README.md`)
  - Objectifs et périmètre fonctionnel définis
  - Découpage en 4 sous-lots (SL1→SL4)
  - Plan d'action séquencé
  - Critères d'acceptation
  - Cas d'usage documentés

### 2. Dépendances

- ✅ **Étape 1 validée** : Service mémoire opérationnel
  - Endpoints fonctionnels (`GET /context`, `POST /interaction`, etc.)
  - Base de données locale accessible
  - Système de gouvernance opérationnel

---

## ❌ CE QUI RESTE À FAIRE

### SL1 – Protocole de communication (1 j)

**Statut** : ❌ Non démarré

**À implémenter** :
- [ ] Spécification du format de message JSON
- [ ] Schémas de validation (JSON Schema)
- [ ] Gestion des sessions multi-agents
- [ ] Protocole de handshake initial
- [ ] Documentation des types d'agents supportés

**Livrables attendus** :
- `protocol_specification.md`
- `message_schema.json`
- Exemples de messages

### SL2 – Service de simulation (2 j)

**Statut** : ❌ Non démarré

**À implémenter** :
- [ ] Service FastAPI pour orchestration
- [ ] Endpoints :
  - `POST /simulation/start`
  - `POST /simulation/{session_id}/message`
  - `GET /simulation/{session_id}/status`
  - `POST /simulation/{session_id}/stop`
- [ ] Logique d'orchestration (boucles de conversation)
- [ ] Intégration avec service mémoire
- [ ] Gestion des timeouts et erreurs
- [ ] Détection de boucles d'erreur

**Livrables attendus** :
- Service FastAPI fonctionnel
- Tests d'intégration avec memory_service

### SL3 – Capture et métriques (1,5 j)

**Statut** : ❌ Non démarré

**À implémenter** :
- [ ] Journalisation des échanges dans la mémoire
  - Création d'`Experience` pour chaque simulation
  - Enrichissement des `InteractionLog` avec métadonnées multi-agent
- [ ] Calcul des métriques comportementales :
  - Variabilité (entropie, diversité)
  - Autonomie (% messages initiés, questions)
  - Curiosité (exploration, profondeur)
  - Cohérence (stabilité personnalité)
- [ ] Format d'export des résultats (JSON)

**Livrables attendus** :
- Module de calcul des métriques
- Format d'export JSON
- Tests de validation des métriques

### SL4 – Interface de supervision (1 j)

**Statut** : ❌ Non démarré

**À implémenter** :
- [ ] CLI pour lancer des simulations
  - `lia-sim start`
  - `lia-sim status`
  - `lia-sim stop`
  - `lia-sim export`
- [ ] Dashboard minimal (terminal)
  - Affichage en temps réel
  - Métriques visuelles
- [ ] Visualisation des échanges
  - Format conversation
  - Export lisible

**Livrables attendus** :
- CLI fonctionnel
- Dashboard terminal minimal
- Documentation d'utilisation

---

## 📊 PROGRESSION PAR SOUS-LOT

| Sous-lot | Statut | Progression | Blocages |
|----------|--------|-------------|----------|
| SL1 – Protocole communication | ❌ Non démarré | 0% | Aucun |
| SL2 – Service simulation | ❌ Non démarré | 0% | Aucun |
| SL3 – Capture & métriques | ❌ Non démarré | 0% | Aucun |
| SL4 – Interface supervision | ❌ Non démarré | 0% | Aucun |

**Progression globale** : **0%** (définition terminée, implémentation à démarrer)

---

## 🎯 PROCHAINES ÉTAPES RECOMMANDÉES

### Phase 1 : Protocole (SL1) - 1 jour
1. Créer `livrables/protocol_specification.md`
2. Définir `message_schema.json` (JSON Schema)
3. Documenter les types d'agents et handshake
4. Valider avec revue technique

### Phase 2 : Service simulation (SL2) - 2 jours
1. Créer structure de base (`simulation_service/`)
2. Implémenter endpoints FastAPI
3. Développer logique d'orchestration
4. Intégrer avec `memory_service`
5. Tests unitaires et d'intégration

### Phase 3 : Capture & métriques (SL3) - 1,5 jours
1. Implémenter journalisation dans mémoire
2. Développer algorithmes de calcul métriques
3. Créer format d'export JSON
4. Tests de validation métriques

### Phase 4 : Interface supervision (SL4) - 1 jour
1. Développer CLI (`lia-sim`)
2. Créer dashboard terminal
3. Implémenter visualisation échanges
4. Documentation utilisateur

---

## ⚠️ RISQUES IDENTIFIÉS

1. **Complexité de l'orchestration** : Gérer plusieurs agents, timeouts, erreurs
   - **Mitigation** : Commencer simple (2 agents), itérer

2. **Coûts API externes** : Si utilisation de LLM externes (OpenAI, etc.)
   - **Mitigation** : Limiter nombre de messages, cache, tests avec agents simulés

3. **Performance** : Calcul métriques en temps réel peut être coûteux
   - **Mitigation** : Calcul asynchrone, agrégation par batch

4. **Boucles d'erreur** : Détection peut être complexe
   - **Mitigation** : Heuristiques simples (répétitions, timeout), tests approfondis

---

## 📝 NOTES

- L'Étape 1 est complète et opérationnelle, ce qui permet de démarrer l'Étape 2 sans blocage.
- Le cahier des charges est détaillé et prêt pour l'implémentation.
- Aucun code n'existe encore pour l'Étape 2.
- Durée estimée totale : **5,5 jours** (selon cahier des charges)

---

## ✅ VALIDATION PRÉALABLE

Avant de démarrer l'implémentation, valider :
- [ ] Cahier des charges approuvé par les parties prenantes
- [ ] Choix des technologies (FastAPI confirmé, choix LLM providers)
- [ ] Architecture technique détaillée (si nécessaire)
- [ ] Environnement de développement prêt

**Recommandation** : Démarrer par SL1 (protocole) pour figer les interfaces avant l'implémentation.

