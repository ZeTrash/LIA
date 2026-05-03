# Guide de migration MemoryRank

Ce document explique comment migrer une base de données existante pour supporter MemoryRank V1 et V2.

## Problème

Si vous avez une base de données créée avant l'ajout de MemoryRank, la table `souvenirs` n'a pas la colonne `memory_rank_score` nécessaire pour le système MemoryRank.

**Erreur typique :**
```
sqlite3.OperationalError: table souvenirs has no column named memory_rank_score
```

## Solution

Utilisez le script de migration automatique :

```bash
cd /opt/LIA
source venv/bin/activate
python scripts/migrate_add_memory_rank_score.py
```

## Ce que fait le script

1. **Vérifie et crée les tables nécessaires**
   - Crée toutes les tables MemoryRank si elles n'existent pas
   - Inclut la table `memory_links` pour le graphe de mémoire

2. **Ajoute la colonne `memory_rank_score`**
   - Vérifie si la colonne existe déjà
   - Ajoute la colonne avec une valeur par défaut de `0.0`
   - Les souvenirs existants reçoivent `memory_rank_score = 0.0`

3. **Vérifie l'intégrité**
   - Confirme que la colonne a été ajoutée
   - Compte les souvenirs existants
   - Vérifie la présence de la table `memory_links`

## Après la migration

### Calculer les scores MemoryRank

Une fois la migration terminée, vous pouvez calculer les scores MemoryRank pour les souvenirs existants :

```python
from memory_service.memory_rank_engine import MemoryRankEngine

engine = MemoryRankEngine()
ranks = engine.compute_and_update_ranks()
print(f"Scores calculés pour {len(ranks)} souvenirs")
```

### Vérifier les scores

```python
from memory_service.store import MemoryStore

store = MemoryStore(use_memory_rank=True)
context = store.get_context(limit_memories=10)
memories = context.get("memories", [])

for memory in memories:
    print(f"MemoryRank: {memory.get('memory_rank_score', 0.0):.6f}")
```

## Migration manuelle (alternative)

Si vous préférez migrer manuellement :

```sql
-- Ajouter la colonne memory_rank_score
ALTER TABLE souvenirs 
ADD COLUMN memory_rank_score REAL DEFAULT 0.0;

-- Vérifier que la colonne existe
PRAGMA table_info(souvenirs);
```

## Tables créées automatiquement

Le script crée également les tables suivantes si elles n'existent pas :

- **`memory_links`** : Liens entre souvenirs pour le graphe MemoryRank
  - `link_id` : ID unique du lien
  - `source_memory_id` : ID du souvenir source
  - `target_memory_id` : ID du souvenir cible
  - `weight` : Poids du lien (force de référence)
  - `link_type` : Type de lien (cooccurrence, similarity, causal, etc.)
  - `link_metadata` : Métadonnées additionnelles (JSON)

## Compatibilité

- ✅ Compatible avec les bases de données existantes
- ✅ Ne supprime aucune donnée existante
- ✅ Ajoute uniquement les colonnes/tables nécessaires
- ✅ Valeurs par défaut sûres (0.0 pour memory_rank_score)

## Dépannage

### La colonne existe déjà
```
✅ La colonne memory_rank_score existe déjà.
   Aucune migration nécessaire.
```
→ Tout est OK, aucune action nécessaire.

### Erreur de permissions
Si vous obtenez une erreur de permissions sur la base de données :
- Vérifiez que le fichier `data/memory.db` est accessible en écriture
- Vérifiez les permissions du répertoire `data/`

### Base de données verrouillée
Si la base de données est verrouillée :
- Fermez toutes les autres connexions à la base
- Attendez quelques secondes et réessayez

## Scripts d'initialisation

Après la migration, tous les scripts d'initialisation fonctionnent correctement :

```bash
# Initialiser l'identité
python scripts/init_lia_identity.py

# Initialiser les capacités
python scripts/init_lia_capabilities.py

# Initialiser la mémoire de démonstration
python scripts/init_lia_demo_memory.py
```

## Notes importantes

1. **Sauvegarde recommandée** : Avant de migrer une base de données en production, faites une sauvegarde :
   ```bash
   cp data/memory.db data/memory.db.backup
   ```

2. **Scores initiaux** : Après la migration, tous les souvenirs ont `memory_rank_score = 0.0`. Les scores seront calculés automatiquement lors de la première utilisation de MemoryRank.

3. **Liens existants** : Si vous avez déjà des liens entre souvenirs, ils seront préservés. Sinon, les liens seront créés automatiquement lors de l'utilisation de MemoryRank V2.

## Vérification post-migration

Pour vérifier que tout fonctionne :

```python
from memory_service.store import MemoryStore
from memory_service.memory_rank_engine import MemoryRankEngine

# Vérifier que la colonne existe
store = MemoryStore()
session = store.db.get_session()
result = session.execute("PRAGMA table_info(souvenirs)")
columns = [row[1] for row in result]
assert 'memory_rank_score' in columns, "Colonne memory_rank_score manquante"

# Vérifier que MemoryRank fonctionne
engine = MemoryRankEngine()
ranks = engine.compute_and_update_ranks()
print(f"✅ Migration réussie : {len(ranks)} scores calculés")
```

