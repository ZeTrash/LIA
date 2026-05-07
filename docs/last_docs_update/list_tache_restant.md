# Plan d'execution - tâches restantes

Ce document transforme la vision PromptBrain + QueryBrain en backlog actionnable.

## 1) Objectif produit

Construire une orchestration en 2 cerveaux:
- `QueryBrain`: récupère de façon autonome les données utiles (mémoire, identité, objectifs, contexte).
- `PromptBrain`: compose un prompt final optimal et ajuste dynamiquement les paramètres d'inférence.

Résultat attendu:
- Réponses plus pertinentes.
- Coût et latence mieux contrôlés.
- Pipeline explicable et testable.

Objectif d'autonomie (prioritaire):
- Minimiser les parcours à choix fixes.
- Basculer vers une prise de décision dynamique pilotée par signaux (intent, confiance, coût, latence, qualité attendue).
- Conserver les menus historiques uniquement comme filet de sécurité.

## 2) Architecture cible (MVP)

Ordre d'exécution:
1. Entrée utilisateur.
2. `QueryBrain` décide des outils à appeler.
3. Agrégation des résultats (avec budget tokens).
4. `PromptBrain` construit le prompt final.
5. Modèle de communication génère la réponse.

Contraintes MVP:
- Pas de liberté SQL brute au début: uniquement via fonctions outillées.
- Chaque étape doit produire des logs structurés.
- Fallback obligatoire si un cerveau échoue.

## 3) Compatibilité transitoire avec l'existant (choix B/G)

Objectif: garantir la non-régression pendant la transition, sans figer l'architecture autour des menus.

### Mapping minimal à préserver

- `B1` (analyser requête) -> classification intent + stratégie de récupération.
- `B2` (rechercher mémoire) -> `search_memory(query, k)`.
- `B3` (connaissance de soi) -> entrée vers `G1/G2/G3/G4/G5`.
- `B4` (patterns préférés) -> récupération des patterns applicables (si activé).
- `B5` (répondre) -> passage à PromptBrain puis génération finale.

- `G1` (identité) -> `get_identity()`.
- `G2` (traits) -> récupération des traits triés par score.
- `G3` (capacités) -> récupération des capacités actives.
- `G4` (souvenirs) -> sous-parcours souvenirs (équivalent menu S).
- `G5` (recherche concept) -> `search_memory(query, k)` élargi.
- `G6` (retour) -> navigation arrière sans perte d'état.

### Règle de migration

- Étape 1 (bootstrap): les choix `B/G` servent de référence de comportement.
- Étape 2 (autonomie assistée): QueryBrain produit un plan autonome + équivalent menu simulé pour audit.
- Étape 3 (autonomie par défaut): le plan autonome devient la source de vérité.
- Les menus `B/G` sont conservés uniquement en fallback si:
  - confiance sous seuil,
  - dépassement budget coût/latence,
  - erreur tool non récupérable.

## 4) Backlog priorisé

### Phase 0 - Cadrage technique (court)
- [ ] Définir les contrats d'entrée/sortie:
  - `QueryBrainInput`, `QueryBrainOutput`
  - `PromptBrainInput`, `PromptBrainOutput`
- [ ] Définir les budgets globaux:
  - `max_tool_calls`
  - `max_context_tokens`
  - `max_latency_ms`
- [ ] Définir les modes de fallback:
  - mode minimal sans mémoire
  - mode avec mémoire récente uniquement

Critères d'acceptation:
- [ ] Les structures I/O sont documentées et versionnées.
- [ ] Les limites de coût/latence sont explicites.

### Phase 1 - QueryBrain (MVP)
- [ ] Exposer un set minimal de tools:
  - `search_memory(query, k)`
  - `get_identity()`
  - `get_recent_episodes(n)`
  - `get_objectives()`
  - `search_by_emotion(emotion)`
- [ ] Implémenter l'orchestration des appels tools (1 à N appels).
- [ ] Ajouter un ordonnanceur simple:
  - arrêter si signal de suffisance atteint
  - respecter `max_tool_calls`
- [ ] Ajouter la normalisation des sorties (format unique).
- [ ] Ajouter un score de confiance de plan (`plan_confidence`).
- [ ] Ajouter une politique de décision:
  - `AUTO` (autonome direct)
  - `AUTO_WITH_AUDIT` (autonome + mapping menu)
  - `SAFE_FALLBACK` (retour menu)

Critères d'acceptation:
- [ ] Sur un lot de prompts de test, QueryBrain récupère des données cohérentes.
- [ ] Aucun dépassement de `max_tool_calls`.
- [ ] En cas d'échec tool, pipeline continue en mode dégradé.
- [ ] Au moins 80% des cas standards passent en mode `AUTO` ou `AUTO_WITH_AUDIT` (sans menu forcé).

### Phase 2 - PromptBrain (MVP)
- [ ] Construire un template de prompt final:
  - identité/personnalité
  - contexte récupéré
  - objectifs actifs
  - consignes de ton/règles
- [ ] Ajouter la sélection contextuelle:
  - inclure uniquement les éléments pertinents
  - couper les éléments à faible score
- [ ] Ajouter la compression:
  - résumé local si dépassement budget tokens
  - fallback vers modèle de résumé plus fort si nécessaire
- [ ] Ajuster les paramètres d'inférence:
  - factuel -> température basse
  - créatif -> température plus haute
  - adapter `top_p` et `max_tokens`

Critères d'acceptation:
- [ ] Le prompt final est généré de manière déterministe à entrée égale (hors stochasticité contrôlée).
- [ ] Le budget tokens est respecté.
- [ ] Les paramètres d'inférence changent selon le type de requête.

### Phase 3 - Observabilité + sécurité opérationnelle
- [ ] Logger chaque run:
  - tools appelés
  - latence par étape
  - tokens in/out
  - stratégie de fallback activée ou non
- [ ] Ajouter des garde-fous:
  - timeout par étape
  - circuit breaker sur tool instable
  - limite de coût par requête
- [ ] Ajouter des métriques d'évaluation offline:
  - pertinence réponse
  - rappel mémoire utile
  - coût moyen par requête
  - taux d'autonomie (`auto_path_rate`)
  - taux de fallback menu (`menu_fallback_rate`)

Critères d'acceptation:
- [ ] Dashboard minimal consultable (même simple CSV/JSON au début).
- [ ] Alertes visibles quand budgets dépassés.
- [ ] Suivi explicite de la baisse continue du `menu_fallback_rate`.

### Phase 4 - Qualité (tests)
- [ ] Tests unitaires:
  - mapping type de requête -> paramètres inférence
  - ranking/filtrage mémoire
- [ ] Tests d'intégration:
  - pipeline complet sur scénarios réels
  - cas d'échec tools
  - vérification des transitions `AUTO -> SAFE_FALLBACK`
- [ ] Jeu d'évaluation:
  - questions factuelles
  - conversations identitaires
  - tâches créatives
  - mémoire longue

Critères d'acceptation:
- [ ] Pipeline stable sur le jeu d'évaluation.
- [ ] Régression détectable avant merge.
- [ ] Aucun scénario critique ne dépend exclusivement d'un choix menu codé en dur.

## 5) Définition du "Done" (MVP)

Le MVP est terminé si:
- [ ] QueryBrain + PromptBrain sont branchés dans le flux principal.
- [ ] Les fallbacks empêchent les pannes bloquantes.
- [ ] Les budgets coût/latence/tokens sont respectés sur le lot de test.
- [ ] Les tests critiques passent en CI.
- [ ] Une documentation d'exploitation existe (runbook court).
- [ ] Le mode autonome est majoritaire en production contrôlée (menus non dominants).

## 6) Suggestions d'implémentation rapide

Pour livrer vite:
- Démarrer avec un modèle léger pour `PromptBrain`.
- Limiter QueryBrain à 3 appels tools max au départ.
- Reporter le Text-to-SQL libre à une phase ultérieure.
- Utiliser des règles explicites avant un comportement entièrement autonome.

## 7) Prochaine action concrète

Première tâche à lancer maintenant:
- [ ] Implémenter les schémas I/O (`QueryBrainInput/Output`, `PromptBrainInput/Output`) + tests unitaires de validation de schéma.
