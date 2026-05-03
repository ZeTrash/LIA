# Archive - Ancien Code du Projet LIA

**Date de sauvegarde** : 2024-12-19  
**Raison** : Refonte complète du projet avec nouvelle architecture alignée sur la vision clarifiée

---

## Contenu de l'Archive

Cette archive contient tout le code et la documentation de l'ancienne version du projet LIA, avant la refonte complète.

### Structure

```
_archive/
├── memory_service/          # Service mémoire (Étape 1)
│   ├── src/                # Code source
│   ├── tests/              # Tests
│   └── README.md
├── simulation_service/      # Service simulation multi-agent (Étape 2)
│   ├── src/                # Code source
│   ├── tests/              # Tests
│   └── README.md
├── charge_timeline/        # Cahiers des charges et livrables
│   ├── etape1_cahier_charges/
│   ├── etape2_simulation_multiagent/
│   ├── etape2_5_migration_gpt2/
│   ├── etape2_6_autonomie_boucle_autonome/
│   └── etape3_interface_supervision/
├── tools/                  # Outils divers
│   └── mock_server/
├── docs/                   # Documentation ancienne
│   ├── ANALYSE_CONCEPT_AUTONOMIE.md
│   ├── architecture.md
│   ├── CONTEXT.md
│   ├── MIGRATION_GPT2_COMPLETE.md
│   └── ...
├── GUIDE_TESTS_ETAPE_2_6.md
├── run_all_tests.py
└── env.example
```

---

## Concepts Récupérés

Les concepts essentiels de cette archive ont été extraits et documentés dans `docs/CONCEPTS_RECUPERES.md` pour être réutilisés dans la nouvelle architecture.

### Concepts Clés Identifiés

1. **Mémoire Persistante**
   - Structure de données (Traits, Souvenirs, Interactions, Experiences)
   - API REST pour accès mémoire
   - Système de gouvernance et scoring
   - Base de données SQLite/PostgreSQL

2. **Architecture Modulaire**
   - Système d'adapters (LocalLLMAdapter, ExternalLLMAdapter)
   - Orchestration multi-agent
   - Portails d'interaction (Autonome, Multi-Agent, Humain)

3. **Autonomie**
   - Scheduler autonome (LIAAutonomousScheduler)
   - Objectifs personnels (PersonalGoals)
   - Auto-recherche, auto-évaluation, auto-réflexion

4. **Modèle Local**
   - LocalLLMAdapter pour GPT-2 Small
   - Intégration avec mémoire
   - Construction de prompts avec contexte

---

## Pourquoi cette Archive ?

Cette archive a été créée dans le cadre d'une refonte complète du projet pour :

1. **Préserver le travail existant** : Tout le code et la documentation sont conservés
2. **Permettre la récupération de concepts** : Les concepts clés peuvent être réutilisés
3. **Référence historique** : Comprendre l'évolution du projet

---

## Nouvelle Architecture

Le nouveau projet suit une architecture clarifiée documentée dans :
- `docs/RESTRUCTURATION_REDEFINITION_RECONCEPTIALISATION.md` (vision)
- `docs/PLAN_REFONTE_PROJET.md` (plan de refonte)

**Différences principales** :
- Architecture plus simple et claire
- Distinction nette entre noyau primaire (GPT-2) et noyau d'appui (Gemini)
- Développement étape par étape avec validation

---

## Utilisation

Cette archive est **en lecture seule**. Elle sert de référence pour :
- Comprendre les concepts implémentés précédemment
- Récupérer des patterns ou structures utiles
- Consulter la documentation historique

**Ne pas modifier** cette archive. Toute nouvelle implémentation doit se faire dans la nouvelle structure du projet.

---

**Note** : Cette archive peut être supprimée une fois la nouvelle architecture complètement implémentée et validée, si souhaité.

