# Gouvernance, Scoring et Règles opérationnelles

## 1. Paramètres globaux

| Nom | Description | Valeur par défaut | Plage autorisée | Stockage |
| --- | --- | --- | --- | --- |
| `w_i` | Poids importance intrinsèque | 0.45 | [0.2 ; 0.6] | `governance_params` scope `souvenir` |
| `w_r` | Poids récence | 0.30 | [0.1 ; 0.5] | idem |
| `w_e` | Poids émotion | 0.15 | [0 ; 0.3] | idem |
| `w_f` | Poids fréquence | 0.10 | [0 ; 0.2] | idem |
| `half_life.fact` | Demi-vie récence faits | 14 jours | 7–60 | scope `souvenir.fact` |
| `half_life.preference` | Demi-vie préférences | 45 jours | 15–180 | scope `souvenir.preference` |
| `half_life.alert` | Demi-vie alertes | 5 jours | 1–30 | scope `souvenir.alert` |
| `drift_threshold_warn` | Seuil alerte dérive | 0.35 | 0.2–0.5 | scope `governance.global` |
| `drift_threshold_block` | Seuil blocage | 0.55 | 0.4–0.8 | idem |
| `score_min_context` | Score mini pour contexte | 0.35 | 0.2–0.6 | scope `context` |
| `purge_interval_min` | Fréquence purge | 60 min | 15–240 | scope `housekeeping` |

## 2. Calcul du score total

Formule utilisée pour classer les souvenirs avant `GET /context` :

```
Recence(delta_t) = e^(-delta_t / half_life(category))
FrequencyBoost(freq) = log1p(freq)
S(memory) = w_i * importance_score
             + w_r * Recence(now - last_seen)
             + w_e * normalized_emotion
             + w_f * FrequencyBoost(frequency)
```

Pseudo-code :

```
function score(memory, now):
    recency = exp(-(now - memory.last_seen) / half_life(memory.category))
    freq_boost = log1p(memory.frequency)
    return w_i*memory.importance_score +
           w_r*recency +
           w_e*normalizeEmotion(memory.emotion_score) +
           w_f*freq_boost
```

Seuls les souvenirs dont `S >= score_min_context` sont éligibles au top-K (K par défaut = 12, paramétrable via requête `max_memories`).

## 3. Ajustements dynamiques

- **Bump récence** : lorsqu’un souvenir est relu, `recency_score = min(1, recency_score + 0.15)` et `frequency += 1`.
- **Saturation tags** : si un tag apparaît >8 fois dans le top-K, on abaisse `importance_score` des entrées les moins récentes (-0.1).
- **Emotion mapping** : valence [-1;1] convertie en `[0,1]` via `(valence + 1)/2` avant application de `w_e`.

## 4. Purge et archivage

Objectifs : maintenir la base <50k souvenirs actifs et garantir pertinence.

```
function purgeJob(now):
    for memory in souvenirs:
        if memory.ttl < now or score(memory, now) < 0.2:
            archive(memory)
            delete(memory)
```

- **Planification** : toutes les heures (`purge_interval_min`).
- **Archivage** : export JSONL vers `archives/souvenirs/YYYY-MM-DD.jsonl.zst`, compression zstd niveau 7, métadonnées (hash, TTL original).
- **Quotas** : si archive >2 Go, purge FIFO des plus anciennes archives (>90 jours).

## 5. Détection de dérive

1. Générer embeddings ton/intent à partir de la réponse (`draft_response`).
2. Calculer `drift_score = cosine_distance(expected_embedding, observed_embedding)`.
3. Appliquer seuils :
   - `drift_score >= drift_threshold_block` → `verdict = block`, rollback du dernier `trait_update` associé à la session.
   - `drift_threshold_warn <= drift_score < drift_threshold_block` → `verdict = warn`, création d’un souvenir `alert`.
4. Journaliser l’évènement dans `indicators` + `request_audit`.

## 6. Cohérence et détection de conflits

- Utiliser `hash` (SHA3-256) sur le contenu normalisé.
- Si `hash` identique mais `source` différente → incrémenter `frequency` au lieu de dupliquer.
- Si `hash` différent mais `tags` identiques → créer entrée `conflict_set` dans `souvenirs_conflicts` (table logique décrite dans README) pour revue humaine.

## 7. Rollback d’un trait

```
function rollbackTrait(trait_id):
    last_version = getLatestVersion(trait_id)
    delta = last_version.delta
    applyInverseDelta(trait_id, delta)
    insert trait_versions entry tagged 'rollback'
    notify supervision
```

Conditions de rollback :
- Drift bloquant
- Contradiction marquée `severity = error`
- Incident manuel de la supervision

## 8. Workflow `POST /governance/check`

1. Vérifier la complétude (`session_id`, `draft_response`, `signals`).
2. Calculer `drift_score`, `coherence_gap`, `toxicity_score` (si signal fourni).
3. Évaluer règles :
   - `coherence_gap > 0.15` → `issues += {code: "COHERENCE_LOW"}`
   - `toxicity_score >= 0.7` → block
   - `pending_incident(session_id)` → warn automatique
4. Si `issues.empty` → `verdict = allow` sinon appliquer hiérarchie `block > warn`.
5. Retourner `auto_fix` (ex : suggestion de reformulation) lorsque possible.

## 9. Scoreboard & critères d’acceptation

- Scoreboard valide si `coverage_traits_pct >= 0.6` **ET** `drift_alerts_count < 3/100 interactions`.
- `POST /governance/check` accepté lorsque 100 % des scénarios de test (liste dans `plan_tests_observabilite.md`) passent en moins de 250 ms.




