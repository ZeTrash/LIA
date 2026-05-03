# Étape 2.5 – Migration vers GPT-2 Small (Modèle Local Vierge)

## Objectif

Migrer LIA d'une architecture basée sur des APIs externes (Gemini, OpenAI) vers un modèle LLM local **vierge** (GPT-2 Small) pour :
- ✅ Obtenir un contrôle total sur la personnalité de LIA
- ✅ Éliminer les dépendances aux APIs externes (coûts, latence, limites)
- ✅ Permettre l'autonomie complète de LIA
- ✅ Utiliser un modèle "vierge" (sans fine-tuning) pour que la personnalité vienne uniquement de la mémoire

## Contexte

**Vision révisée** : LIA doit être un agent **autonome** qui fonctionne de lui-même, développe sa personnalité par auto-apprentissage, et peut interagir avec d'autres agents pour s'auto-évaluer.

**Problème actuel** : L'architecture utilise des APIs externes (Gemini, OpenAI) qui :
- Nécessitent une connexion internet
- Coûtent de l'argent
- Ont des limites de rate
- Ne permettent pas l'autonomie complète

**Solution** : GPT-2 Small (124M paramètres, ~125 MB en INT4)
- Modèle de base (vierge, pas de fine-tuning)
- Ultra-léger (fonctionne sur CPU)
- Local (pas de dépendance externe)
- Contrôle total sur la personnalité

## Livrables attendus

- **LocalLLMAdapter** : Adapter pour GPT-2 Small remplaçant les APIs externes
- **Intégration avec mémoire** : Le prompt inclut automatiquement traits + souvenirs
- **Quantisation** : Modèle optimisé en INT4/INT8 pour réduire la taille
- **Tests de validation** : Vérifier que LIA génère des réponses cohérentes avec sa personnalité
- **Documentation technique** : Guide d'installation, configuration, troubleshooting
- **Migration progressive** : Système de fallback (API externe si local échoue)

## Périmètre fonctionnel

1. **Remplacement des adapters externes** : Créer `LocalLLMAdapter` pour GPT-2 Small
2. **Intégration mémoire** : Construire le prompt avec contexte (traits + souvenirs)
3. **Optimisation** : Quantisation du modèle pour réduire la taille mémoire
4. **Gestion des erreurs** : Fallback vers API externe si le modèle local échoue
5. **Tests** : Validation que les réponses sont cohérentes avec la personnalité stockée

## Découpage des charges

| Module | Description | Tâches clés | Sorties |
| --- | --- | --- | --- |
| **LocalLLMAdapter** | Adapter pour GPT-2 Small | - Installation transformers + torch<br>- Chargement du modèle GPT-2 Small<br>- Quantisation INT4/INT8<br>- Méthode `send_message()` avec prompt construit | Code `LocalLLMAdapter` fonctionnel |
| **Construction prompt** | Intégrer mémoire dans le prompt | - Récupérer contexte depuis memory_service<br>- Formater traits + souvenirs en prompt<br>- Gérer la limite de tokens | Fonction `build_prompt(context, message)` |
| **Optimisation** | Réduire taille et latence | - Quantisation dynamique<br>- Cache du modèle en mémoire<br>- Gestion GPU optionnelle | Modèle optimisé < 200 MB RAM |
| **Tests & validation** | Vérifier le fonctionnement | - Tests unitaires LocalLLMAdapter<br>- Tests d'intégration avec mémoire<br>- Validation qualité des réponses | Suite de tests + rapport |
| **Documentation** | Guide complet | - Installation<br>- Configuration<br>- Troubleshooting<br>- Exemples d'utilisation | Documentation technique complète |

## Organisation des travaux

| Sous-lot | Objectif | Livrables | Durée cible |
| --- | --- | --- | --- |
| **SL1 – Installation & Adapter** | Créer LocalLLMAdapter fonctionnel | Code LocalLLMAdapter, tests basiques | 1 j |
| **SL2 – Intégration mémoire** | Construire prompt avec contexte | Fonction build_prompt, tests avec mémoire | 0,5 j |
| **SL3 – Optimisation** | Quantiser et optimiser le modèle | Modèle quantifié, cache, tests performance | 0,5 j |
| **SL4 – Tests & documentation** | Valider et documenter | Suite de tests, documentation complète | 0,5 j |

**Durée totale estimée : 2,5 jours**

## Plan d'action séquencé

1. **Installation dépendances** (0,5 j) : transformers, torch, configuration
2. **Création LocalLLMAdapter** (0,5 j) : Code de base, chargement modèle
3. **Intégration mémoire** (0,5 j) : Construction prompt avec contexte
4. **Optimisation** (0,5 j) : Quantisation, cache, tests performance
5. **Tests & documentation** (0,5 j) : Validation complète, documentation

## Critères d'acceptation

- ✅ `LocalLLMAdapter` peut générer des réponses avec GPT-2 Small
- ✅ Le prompt inclut automatiquement les traits et souvenirs de LIA
- ✅ Les réponses sont cohérentes avec la personnalité stockée dans la mémoire
- ✅ Le modèle utilise < 200 MB de RAM (quantisé)
- ✅ Fallback vers API externe si le modèle local échoue
- ✅ Documentation complète disponible
- ✅ Tests passent avec succès

## Risques et mitigations

- **Qualité limitée** : GPT-2 Small est basique → Mitigation : Fallback API externe, fine-tuning optionnel futur
- **Latence** : Modèle local peut être plus lent → Mitigation : Cache, optimisation, GPU optionnel
- **Mémoire** : Modèle peut consommer beaucoup de RAM → Mitigation : Quantisation INT4, chargement à la demande
- **Compatibilité** : Problèmes de dépendances → Mitigation : Environnement virtuel isolé, documentation détaillée

## Dépendances

- ✅ **Étape 1** : Infrastructure de mémoire persistante (prérequis absolu)
  - Service mémoire opérationnel (`GET /context`)
  - Base de données locale accessible
- ✅ **Étape 2** : Simulation multi-agent (pour tester l'intégration)

## Prochaines étapes après l'étape 2.5

- **Étape 3** : Interface de supervision avancée (ajustement des traits en direct)
- **Étape 2.6** (future) : Boucle autonome (scheduler pour auto-recherche, auto-évaluation)

## Architecture technique

```
┌─────────────────────────────────────────┐
│         LIA Core                        │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐                   │
│  │ LocalLLMAdapter  │                   │
│  │ (GPT-2 Small)    │                   │
│  └────────┬─────────┘                   │
│           │                              │
│           │ build_prompt(context, msg)   │
│           │                              │
│           ▼                              │
│  ┌──────────────────┐                   │
│  │  GPT-2 Small     │                   │
│  │  (124M, 125MB)   │                   │
│  └────────┬─────────┘                   │
│           │                              │
│           │ Réponse générée             │
│           │                              │
│           ▼                              │
│  ┌──────────────────┐                   │
│  │  Memory Service  │                   │
│  │  (Journalisation)│                   │
│  └──────────────────┘                   │
└─────────────────────────────────────────┘
```

## Migration progressive

**Phase 1** : LocalLLMAdapter créé, testé en parallèle des APIs externes
**Phase 2** : Remplacement progressif (50% local, 50% API)
**Phase 3** : 100% local avec fallback API si erreur
**Phase 4** : Optionnel - Fine-tuning GPT-2 sur personnalité de LIA

---

## Livrables détaillés

### 1. LocalLLMAdapter

**Fichier** : `simulation_service/src/simulation_service/adapters.py`

**Fonctionnalités** :
- Chargement GPT-2 Small via transformers
- Quantisation INT4/INT8
- Construction prompt avec contexte mémoire
- Gestion cache modèle
- Fallback API externe si erreur

### 2. Construction du prompt

**Format** :
```
[Traits de personnalité]
- Curiosité: 0.85
- Ton: calme et réfléchi
- ...

[Souvenirs pertinents]
- Souvenir 1: ...
- Souvenir 2: ...

[Objectifs de session]
- Objectif 1: ...

[Message utilisateur]
{message}
```

### 3. Optimisation

- Quantisation dynamique (INT4)
- Cache du modèle en mémoire
- Gestion GPU optionnelle (CUDA si disponible)

### 4. Tests

- Tests unitaires LocalLLMAdapter
- Tests d'intégration avec memory_service
- Tests de performance (latence, mémoire)
- Validation qualité des réponses

### 5. Documentation

- Guide d'installation
- Configuration
- Troubleshooting
- Exemples d'utilisation
- Comparaison avant/après migration



