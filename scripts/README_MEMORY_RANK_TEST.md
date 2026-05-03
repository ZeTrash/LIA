# Script de validation MemoryRank

## Description

Le script `test_memory_rank_validation.py` est un outil complet pour tester et valider le système MemoryRank. Il exécute une série de tests couvrant toutes les fonctionnalités du système.

## Utilisation

### Exécution basique

```bash
cd /opt/LIA
source venv/bin/activate
python scripts/test_memory_rank_validation.py
```

**Important :** Le script utilise automatiquement une base de données de test séparée (`data/test.db`) pour ne pas affecter votre base de données principale (`data/memory.db`).

### Options disponibles

```bash
# Utiliser une copie de memory.db comme base de test
python scripts/test_memory_rank_validation.py --use-existing

# Garder la base de données de test après les tests (pour inspection)
python scripts/test_memory_rank_validation.py --keep-db

# Combinaison des deux options
python scripts/test_memory_rank_validation.py --use-existing --keep-db
```

### Exécution avec sortie détaillée

Le script affiche automatiquement :
- Les étapes de chaque test
- Les résultats intermédiaires
- Les validations
- Un résumé final avec le nombre de tests réussis

## Tests exécutés

### 1. Test MemoryRank de base
- Crée 5 souvenirs
- Crée un graphe en étoile (souvenir central)
- Ajoute un cycle pour tester la convergence
- Calcule les scores MemoryRank
- Valide que les scores sont calculés correctement

### 2. Test de décroissance temporelle
- Crée des souvenirs avec différents âges
- Active la décroissance temporelle
- Vérifie que les souvenirs récents ont des scores plus élevés

### 3. Test de détection de co-occurrences
- Crée des souvenirs avec des mots-clés
- Crée une interaction mentionnant ces souvenirs
- Détecte automatiquement les co-occurrences
- Valide la création de liens

### 4. Test de score hybride
- Teste le calcul de score avec MemoryRank seul
- Teste avec MemoryRank + Reward
- Teste avec MemoryRank + Reward + Similarité
- Valide que les scores sont dans les plages attendues

### 5. Test d'intégration RL
- Crée un souvenir
- Applique une récompense RL
- Vérifie que le score d'importance est mis à jour

### 6. Test de hiérarchie fractale
- Crée des souvenirs avec différents niveaux (event, episode, concept, objective)
- Crée des liens hiérarchiques
- Calcule les scores par niveau
- Valide la structure hiérarchique

### 7. Test d'intégration avec get_context()
- Crée 10 souvenirs
- Crée un graphe complexe
- Récupère le contexte avec MemoryRank
- Valide que les souvenirs sont triés par MemoryRank

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
                    VALIDATION DU SYSTÈME MEMORYRANK
======================================================================

ℹ Initialisation de la base de données...
✓ Base de données initialisée

▶ Test 1 : MemoryRank de base
ℹ Création de 5 souvenirs...
✓ Souvenir créé : a1b2c3d4... - 'Souvenir 1 : Information importante...'
...

▶ Test 2 : Décroissance temporelle
...

======================================================================
                          RÉSUMÉ DES TESTS
======================================================================

✓ PASS - basic
✓ PASS - temporal
✓ PASS - cooccurrence
✓ PASS - hybrid
✓ PASS - rl
✓ PASS - fractal
✓ PASS - integration

Résultat : 7/7 tests réussis
✓ Tous les tests sont passés !
```

## Base de données de test

Le script utilise automatiquement une base de données de test séparée (`data/test.db`) pour ne pas affecter votre base de données principale (`data/memory.db`).

### Comportement par défaut

- **Création automatique** : Une nouvelle base de données de test est créée à chaque exécution
- **Nettoyage automatique** : La base de données de test est supprimée après les tests (sauf si `--keep-db` est utilisé)

### Options de base de données

1. **Base de test vierge** (par défaut)
   - Crée une nouvelle base de données vide
   - Idéal pour des tests isolés et reproductibles

2. **Copie de memory.db** (`--use-existing`)
   - Copie `memory.db` vers `test.db` avant les tests
   - Utile pour tester avec vos données existantes
   - Les modifications restent dans `test.db`, `memory.db` n'est pas affectée

3. **Conserver la base de test** (`--keep-db`)
   - Garde `test.db` après les tests
   - Permet d'inspecter les résultats avec un outil SQLite

### Exemple d'utilisation

```bash
# Test avec base vierge (par défaut)
python scripts/test_memory_rank_validation.py

# Test avec vos données existantes
python scripts/test_memory_rank_validation.py --use-existing

# Garder la base de test pour inspection
python scripts/test_memory_rank_validation.py --keep-db

# Inspecter la base de test
sqlite3 data/test.db "SELECT * FROM souvenirs LIMIT 5;"
```

## Dépannage

### Erreur : "Module not found"
Assurez-vous d'être dans l'environnement virtuel :
```bash
source venv/bin/activate
```

### Erreur : "Database locked"
Fermez toutes les autres connexions à la base de données avant d'exécuter le script.

### Erreur : "MemoryRank non activé"
Le script active MemoryRank par défaut. Si vous voyez cette erreur, vérifiez que les dépendances sont installées :
```bash
pip install -r memory_service/requirements.txt
```

## Personnalisation

Vous pouvez modifier le script pour :
- Ajouter vos propres tests
- Modifier les paramètres (nombre de souvenirs, poids des liens, etc.)
- Tester des scénarios spécifiques

## Intégration CI/CD

Le script retourne un code de sortie :
- `0` : Tous les tests sont passés
- `1` : Au moins un test a échoué

Cela permet de l'intégrer dans un pipeline CI/CD :

```bash
python scripts/test_memory_rank_validation.py
if [ $? -eq 0 ]; then
    echo "Tests réussis"
else
    echo "Tests échoués"
    exit 1
fi
```

