# Script de validation MemoryRank V2

## Description

Le script `test_memory_rank_v2_validation.py` est un outil complet pour tester et valider le système MemoryRank V2 (traitement par phrases). Il exécute une série de tests couvrant toutes les fonctionnalités du système V2.

## Utilisation

### Exécution basique

```bash
cd /opt/LIA
source venv/bin/activate
python scripts/test_memory_rank_v2_validation.py
```

**Important :** Le script utilise automatiquement une base de données de test séparée (`data/test_v2.db`) pour ne pas affecter votre base de données principale.

### Options disponibles

```bash
# Utiliser une copie de memory.db comme base de test
python scripts/test_memory_rank_v2_validation.py --use-existing

# Garder la base de données de test après les tests (pour inspection)
python scripts/test_memory_rank_v2_validation.py --keep-db

# Combinaison des deux options
python scripts/test_memory_rank_v2_validation.py --use-existing --keep-db
```

## Tests exécutés

### 1. Test de segmentation
- Teste la segmentation de différents types de textes
- Vérifie le filtrage des phrases non informatives
- Valide la détection des questions/exclamations

### 2. Test de calcul de nouveauté
- Crée des souvenirs existants
- Teste le calcul de nouveauté pour différentes phrases
- Vérifie que les phrases nouvelles ont un score élevé
- Vérifie que les phrases redondantes ont un score faible

### 3. Test de filtrage sémantique
- Teste le filtrage complet avec score d'importance
- Vérifie que seules les phrases importantes sont stockées
- Valide le filtrage des phrases redondantes

### 4. Test de création de liens
- Teste la création automatique de liens de co-occurrence
- Teste la détection de similarité sémantique
- Vérifie que les liens sont correctement créés

### 5. Test du processeur complet
- Teste le pipeline end-to-end complet
- Segmentation → Filtrage → Stockage → Liens
- Vérifie que les phrases sont correctement stockées

### 6. Test de filtrage de redondance
- Teste avec des interactions similaires
- Vérifie que le système évite la duplication
- Valide la gestion de la redondance

### 7. Test d'intégration MemoryRank
- Teste l'intégration avec MemoryRank V1
- Vérifie que les scores MemoryRank sont calculés
- Valide que les phrases sont correctement liées

## Sortie du script

Le script affiche :
- Des en-têtes colorés pour chaque section
- Des messages de succès (✓) en vert
- Des avertissements (⚠) en jaune
- Des erreurs (✗) en rouge
- Des informations (ℹ) en bleu
- Un résumé final avec le nombre de tests réussis

## Exemple de sortie

```
======================================================================
                VALIDATION DU SYSTÈME MEMORYRANK V2
======================================================================

ℹ Configuration de la base de données de test...
✓ Base de données de test initialisée

▶ Test 1 : Segmentation en phrases
ℹ Test 1: 'Je préfère Python à Java. J'aime travailler sur des...'
  → 2 phrase(s) segmentée(s)
    1. 'Je préfère Python à Java'
    2. 'J'aime travailler sur des projets d'IA'
✓ Segmentation fonctionne (8 phrases au total)

▶ Test 2 : Calcul de nouveauté
...

======================================================================
                        RÉSUMÉ DES TESTS
======================================================================

✓ PASS - segmentation
✓ PASS - novelty
✓ PASS - filtering
✓ PASS - linking
✓ PASS - processor
✓ PASS - redundancy
✓ PASS - integration

Résultat : 7/7 tests réussis
✓ Tous les tests sont passés !
```

## Base de données de test

Le script utilise automatiquement une base de données de test séparée (`data/test_v2.db`) pour ne pas affecter votre base de données principale (`data/memory.db`).

### Comportement par défaut

- **Création automatique** : Une nouvelle base de données de test est créée à chaque exécution
- **Nettoyage automatique** : La base de données de test est supprimée après les tests (sauf si `--keep-db` est utilisé)

### Options de base de données

1. **Base de test vierge** (par défaut)
   - Crée une nouvelle base de données vide
   - Idéal pour des tests isolés et reproductibles

2. **Copie de memory.db** (`--use-existing`)
   - Copie `memory.db` vers `test_v2.db` avant les tests
   - Utile pour tester avec vos données existantes

3. **Conserver la base de test** (`--keep-db`)
   - Garde `test_v2.db` après les tests
   - Permet d'inspecter les résultats avec un outil SQLite

## Dépannage

### Erreur : "Module not found"
Assurez-vous d'être dans l'environnement virtuel :
```bash
source venv/bin/activate
```

### Erreur : "Database locked"
Fermez toutes les autres connexions à la base de données avant d'exécuter le script.

### Erreur : "PhraseMemoryProcessor non disponible"
Vérifiez que tous les fichiers V2 sont présents :
- `memory_service/phrase_segmenter.py`
- `memory_service/semantic_filter.py`
- `memory_service/phrase_memory_processor.py`

## Comparaison avec le script V1

| Fonctionnalité | V1 | V2 |
|----------------|----|----|
| Tests MemoryRank de base | ✅ | ✅ |
| Tests de décroissance temporelle | ✅ | ✅ |
| Tests de co-occurrences | ✅ | ✅ |
| Tests de score hybride | ✅ | ✅ |
| Tests d'intégration RL | ✅ | ✅ |
| Tests de hiérarchie fractale | ✅ | ✅ |
| **Tests de segmentation** | ❌ | ✅ |
| **Tests de nouveauté** | ❌ | ✅ |
| **Tests de filtrage sémantique** | ❌ | ✅ |
| **Tests de création de liens** | ❌ | ✅ |
| **Tests de filtrage de redondance** | ❌ | ✅ |

## Intégration CI/CD

Le script retourne un code de sortie :
- `0` : Tous les tests sont passés
- `1` : Au moins un test a échoué

Cela permet de l'intégrer dans un pipeline CI/CD :

```bash
python scripts/test_memory_rank_v2_validation.py
if [ $? -eq 0 ]; then
    echo "Tests V2 réussis"
else
    echo "Tests V2 échoués"
    exit 1
fi
```

## Exécution des deux scripts

Pour tester à la fois V1 et V2 :

```bash
# Tester V1
python scripts/test_memory_rank_validation.py

# Tester V2
python scripts/test_memory_rank_v2_validation.py
```

Les deux scripts utilisent des bases de données de test séparées et ne s'interfèrent pas.

