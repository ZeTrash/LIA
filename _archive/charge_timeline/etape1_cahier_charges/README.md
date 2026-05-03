# Étape 1 – Infrastructure de mémoire persistante

## Objectif
Construire la couche mémoire locale qui conserve personnalité, souvenirs et règles évolutives, et définir l’API que le moteur LLM utilisera avant/après chaque génération.

## Livrables attendus
- Schéma logique des objets mémoire (traits, souvenirs, expériences, métriques).
- API de lecture/écriture documentée (contrats avant et après génération).
- Règles de gouvernance des données : scoring, durée de vie, contrôles de cohérence.
- Plan de tests et métriques de validation (cohérence, dérive, disponibilité).

## Périmètre fonctionnel
1. **Lecture pré-génération** : fournir au LLM un paquet de contexte (traits actifs, souvenirs prioritaires, objectifs de session).
2. **Écriture post-génération** : journaliser interactions, insights et ajustements de traits avec métadonnées (timestamp, score, source).
3. **Garde-fous** : vérifications automatiques pour empêcher les dérives de personnalité et détecter les incohérences.
4. **Observabilité** : exposer des indicateurs (variabilité, curiosité, cohérence) à la supervision humaine.

## Découpage des charges
| Module | Description | Tâches clés | Sorties |
| --- | --- | --- | --- |
| Modèle de données | Concevoir les entités (Traits, Souvenirs, Expériences, Indicateurs, Paramètres de gouvernance). | - Définir attributs obligatoires/optionnels<br>- Spécifier relations et règles de rétention<br>- Prévoir indexation et priorisation | Schéma JSON/SQL + dictionnaire de données |
| Service mémoire | API locale accessible par le moteur | - Endpoints GET /context, POST /interaction, POST /trait-update<br>- Gestion transactionnelle et versioning des traits | Spécification d’API + pseudo-code d’implémentation |
| Gouvernance & scoring | Gestion des poids, importance et durée de vie | - Algorithmes de scoring (récence, fréquence, émotion)<br>- Règles de purge/archivage<br>- Alertes sur dérive | Règles métier + scripts de validation |
| Observabilité | Donner de la visibilité à l’humain | - Tableau de bord minimal (CLI ou UI simple)<br>- Export métriques (JSON/CSV)<br>- Seuils d’alerte | Description du dashboard + format de logs |

## Organisation des travaux
| Sous-lot | Objectif | Livrables | Durée cible |
| --- | --- | --- | --- |
| SL1 – Modèle de données | Figer le schéma mémoire et la taxonomie des souvenirs/traits. | Schéma + dictionnaire + règles de rétention. | 1,5 j |
| SL2 – Service mémoire | Définir l’API et le flow de lecture/écriture. | Contrats d’API, séquence d’appels, pseudo-code. | 1,5 j |
| SL3 – Gouvernance & scoring | Encadrer les mises à jour et éviter la dérive. | Algorithmes de scoring, règles de purge, checklists de cohérence. | 1 j |
| SL4 – Observabilité | Donner outils de suivi aux humains. | Spécification dashboard, format d’exports, seuils d’alerte. | 0,5 j |

Chaque sous-lot possède son propre responsable, sa short-list de validations et une démonstration rapide : revue de schéma pour SL1, mock d’API pour SL2, scénarios de dérive contrôlée pour SL3, aperçu du dashboard/CLI pour SL4. Les sous-lots peuvent se chevaucher légèrement mais un jalon ne commence qu’une fois les dépendances critiques validées (ex. SL2 attend la version α du schéma de SL1).

## Plan d’action séquencé
1. **Inventaire des cas d’usage** (0,5 j) : définir les types d’interactions à mémoriser.
2. **Modélisation des entités** (1 j) : produire le schéma et valider avec les parties prenantes.
3. **Spécification API** (1 j) : rédiger contrats, payloads exemples, scénarios d’erreur.
4. **Conception du pipeline de cohérence** (0,5 j) : règles, seuils, processus d’escalade.
5. **Plan de tests & observabilité** (0,5 j) : scénarios, indicateurs, outils de suivi.

## Critères d’acceptation
- Le LLM peut récupérer un contexte structuré <200 ms et <10 KB.
- Chaque interaction génère un enregistrement avec score, importance, lien vers traits impactés.
- Les règles de cohérence couvrent au moins : dérive de ton, contradictions factuelles, saturation mémoire.
- Tableaux de bord/exports disponibles pour la supervision.

## Risques et mitigations
- **Explosion de volume** : instaurer TTL et archivage.
- **Incohérences concurrentes** : versionner les traits, verrouillages optimistes.
- **Complexité excessive** : commencer avec JSON/SQLite local avant industrialisation.

## Prochaines étapes après l’étape 1
- Étape 2 : simulation multi-agent branchée sur la mémoire locale.
- Étape 3 : interface de supervision avancée (ajustement des traits en direct).

---

## Livrables détaillés – Étape 1

### 1. Inventaire des cas d’usage (0,5 j)

| Cas d’usage | Déclencheur | Données captées | Impact mémoire |
| --- | --- | --- | --- |
| Conversation courante | Ouverture d’une session utilisateur | Profil session, objectifs déclarés, humeur détectée | Active traits pertinents et objectifs |
| Découverte d’un fait nouveau | L’utilisateur apporte une information factuelle | Contenu brut, source, confiance, lien vers traits concernés | Création d’un souvenir long terme + index thématique |
| Correction / contradiction | L’utilisateur corrige le LLM | Interaction complète, élément contradit, justification, émotion | Marquage du souvenir obsolète + création d’un incident de cohérence |
| Préférence personnelle | L’utilisateur précise un style/une contrainte | Type de préférence, granularité, validité temporelle | Mise à jour d’un trait « style » avec versioning |
| Signal émotionnel | Détection de sentiment fort ou feedback | Sentiment, intensité, contexte, trace audio/texte | Alimente score émotionnel des souvenirs + indicateur de dérive de ton |
| Insight système | Autodiagnostic du LLM (incertitude, fail) | Type d’alerte, palier de confiance, action proposée | Stockage dans Expériences + déclenchement garde-fou |
| Boucle d’apprentissage externe | Import manuel de la supervision humaine | Ticket, labels, verdict, actions à appliquer | Synchronisation forcée des traits et purge ciblée |

Chaque cas d’usage précise : priorité (critique, élevée, normale), besoin de synchronisation (immédiat vs batch), et durée de vie nominale (cf. règles SL3).

### 2. SL1 – Modèle de données

#### 2.1 Entités principales

| Entité | Description | Attributs essentiels |
| --- | --- | --- |
| `Trait` | Profil persistant (valeurs, ton, compétences) | `trait_id`, `type`, `label`, `value`, `version`, `weight`, `confidence`, `last_update`, `origin`, `status` |
| `Souvenir` | Fragment contextuel réutilisable | `memory_id`, `category` (fact, preference, alert), `content`, `tags`, `importance_score`, `recency_score`, `emotion_score`, `ttl`, `source`, `link_refs[]`, `hash` |
| `InteractionLog` | Trace brute post-génération | `interaction_id`, `session_id`, `timestamp`, `prompt`, `response`, `scores{}`, `derived_traits[]`, `anomalies[]` |
| `Experience` | Agrégation d’interactions (ex: projet, sprint) | `experience_id`, `title`, `period`, `outcome`, `metrics_snapshot`, `related_memories[]` |
| `SessionGoal` | Objectifs actifs pour la génération courante | `goal_id`, `session_id`, `priority`, `description`, `blocking_conditions`, `expires_at` |
| `Indicator` | Valeur d’observabilité calculée | `indicator_id`, `type`, `value`, `window`, `status`, `thresholds`, `history[]` |
| `GovernanceParams` | Paramètres dynamiques | `param_id`, `scope`, `value`, `default`, `min/max`, `updated_at`, `updated_by` |

#### 2.2 Relations et règles

- `Souvenir.link_refs` peut cibler `Trait`, `Experience` ou `InteractionLog` (clé composite type + id).
- Un `Trait` exposé au LLM doit être **en statut `active`** et dans sa version la plus récente (verrou optimiste `version`).
- Les `InteractionLog` de sévérité ≥ warning doivent créer un `Souvenir` automatique classé `alert`.
- TTL par défaut : `Souvenir.fact` 45 jours, `Souvenir.preference` 180 jours, `Souvenir.alert` 15 jours. Les TTL dynamiques sont stockés dans `GovernanceParams`.
- Index recommandés : `(category, importance_score DESC)`, `(tags, recency_score DESC)`, `(trait_id, version DESC)`.

#### 2.3 Exemple de paquet mémoire (JSON)

```json
{
  "traits": [
    {"trait_id": "tone", "value": "curieux mais calme", "version": 7, "weight": 0.82}
  ],
  "session_goals": [
    {"goal_id": "g-482", "description": "Préparer un résumé de meeting", "priority": 0.9}
  ],
  "memories": [
    {
      "memory_id": "m-9021",
      "category": "fact",
      "content": "Alice dirige le pôle Produit depuis 2023.",
      "importance_score": 0.76,
      "recency_score": 0.65,
      "link_refs": [{"type": "trait", "id": "stakeholders"}]
    }
  ],
  "indicators": {
    "coherence_score": 0.93,
    "drift_alert": false
  },
  "governance_metadata": {
    "context_version": "2024.12.07-01",
    "build_time_ms": 148
  }
}
```

#### 2.4 Priorisation

Score total `S` d’un souvenir :  
`S = w_i * importance_score + w_r * Recence(delta_t) + w_e * emotion_score + w_f * log1p(frequency)`.  
Le top-K (par défaut K=12) est envoyé dans le contexte pré-génération, sous la contrainte `<10 KB`.

### 3. SL2 – Service mémoire (API locale)

#### 3.1 Principes généraux

- API HTTP locale (127.0.0.1) ou gRPC, délai cible `<200 ms`.
- Chaque requête porte `session_id`, `actor` (LLM / supervision) et `context_version`.
- Réponses signent les ensembles renvoyés via `context_checksum` (SHA-256) pour détecter les divergences.

#### 3.2 Endpoints

1. `GET /context`
   - Requêtes : `session_id`, `max_memories`, `goal_scope`, `flags` (ex: `include_indicators`).
   - Réponses : paquet JSON ci-dessus + `trace_id`, `build_time_ms`, `cache_hit`.
   - Erreurs : `409` si version obsolète, `503` si store indisponible.

2. `POST /interaction`
   - Payload : prompt, réponse, scores (utile, cohérence, ton), émotions détectées, décisions (souvenir créé ?, TTL suggéré).
   - Effets : création `InteractionLog`, éventuel `Souvenir`, mise à jour métriques.
   - Idempotence via `interaction_id`.

3. `POST /trait-update`
   - Payload : `trait_id`, `delta`, `reason`, `source`, `expected_version`.
   - Retour : nouvelle version, `version_token`, `review_required` (bool).
   - Conflit : `409` si version mismatch → le LLM reçoit la dernière version + instructions de merge.

4. `POST /governance/check`
   - Entrée : `session_id`, `draft_response`, `signals`.
   - Sortie : `verdict` (allow, warn, block), `issues[]`, `auto_fix`.

5. `GET /metrics`
   - Expose indicateurs agrégés (latence, taux de purge, dérives).

#### 3.3 Séquence type

1. `GET /context` avant génération → assemble traits actifs + top-K souvenirs + objectifs.
2. LLM génère sa réponse.
3. `POST /interaction` journalise la réponse + signaux.
4. `POST /trait-update` facultatif si apprentissage.
5. `POST /governance/check` peut être invoqué en synchrone (hard guardrail) ou asynchrone.

### 4. SL3 – Gouvernance & scoring

- **Formule de récence** : `Recence(delta_t) = e^(-delta_t / half_life)` avec `half_life` paramétré par catégorie.
- **Score d’émotion** : normalisé [-1,1] → converti en poids via `w_e`.
- **Durée de vie** :
  - Préférences : TTL 6 mois, purge soft → archivage compressé.
  - Faits : TTL 45 jours + rafraîchissement automatique lorsqu’ils sont relus (bump recency).
  - Alertes : TTL 15 jours, mais verrou si incident ouvert.
- **Contrôle de dérive** :
  - Calcul `drift_score = |expected_tone - observed_tone|`.
  - Seuils : `≥0.35` → alerte, `≥0.55` → blocage + rollback dernière mise à jour de trait.
- **Cohérence** :
  - Chaque souvenir stocke `hash` du contenu. Si nouvel enregistrement même `hash` mais source différente, on incrémente fréquence plutôt que dupliquer.
  - Conflit : si `hash` différent mais `tags` identiques, on crée un `conflict_set` à résoudre (revue humaine).
- **Versioning des traits** : optimistic locking, historique conservé 30 versions, delta compressé.
- **Purge/archivage** :
  - Batch horaire → supprime souvenirs `S < 0.2` + TTL expiré.
  - Archivage quotidien vers JSONL compressé (fine-tuning futur).

### 5. SL4 – Observabilité & plan de tests

#### 5.1 Indicateurs clés

| KPI | Description | Seuil/alerte |
| --- | --- | --- |
| `latency_context_ms` | Temps de réponse `GET /context` | Alerte > 180 ms |
| `context_payload_bytes` | Taille du paquet envoyé | Alerte > 9 KB (pré saturation) |
| `coverage_traits_pct` | % de traits actifs utilisés / total disponibles | Alerte < 60 % |
| `coherence_score` | Score moyen post-génération | Alerte < 0.85 |
| `drift_alerts_count` | Nb d’alertes ton/dérive par 100 interactions | Alerte ≥ 3 |
| `ttl_purge_rate` | % de souvenirs purgeables | Alerte > 25 % (trop de bruit) |
| `store_availability` | Disponibilité service mémoire | Alerte < 99.5 % |

Dashboard minimal : CLI/terminal affichant les KPI, export JSON/CSV via `GET /metrics?format=csv`, intégration optionnelle Prometheus (`/metrics/prom`).

#### 5.2 Plan de tests

- **Schéma & data** : validation JSON Schema, tests de migration (upgrade/downgrade), injection de doublons/hash collisions.
- **API** : tests contractuels (exemples Postman), tests de charge (200 req/s burst), tests d’idempotence (`interaction_id` répété).
- **Gouvernance** : scénarios de dérive (ton agressif, contradiction), vérification du rollback de trait, purge TTL contrôlée.
- **Observabilité** : vérification export CSV, compatibilité Prometheus, simulation indisponibilité store (chaos test).
- **Critères d’acceptation** : latence <200 ms, payload <10 KB, logs complets avec score/importance, garde-fous ton/fait/saturation actifs.
