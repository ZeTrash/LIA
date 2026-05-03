# Guide d'organisation et de supervision du workspace LIA

## Règles de supervision

Ce document décrit les règles et bonnes pratiques pour maintenir l'organisation du workspace LIA.

## Principes fondamentaux

### 1. Séparation claire des responsabilités

- **Documentation** : Toujours dans `docs/` ou `charge_timeline/`
- **Code source** : Dans les dossiers de services (ex: `memory_service/src/`)
- **Configuration** : Uniquement dans `config/` avec templates `.example`
- **Données** : Dans `data/` des services respectifs, jamais versionnées

### 2. Sécurité des informations sensibles

**Règle absolue** : Aucun fichier contenant des secrets ne doit être versionné.

Fichiers à exclure systématiquement :
- `config/api.conf` (clés API)
- `.env` (variables d'environnement)
- `*.db` (bases de données)
- Tous les fichiers contenant `_secret`, `_key`, `_token`

**Action** : Toujours créer un fichier `.example` comme template.

### 3. Documentation à jour

Chaque composant majeur doit avoir :
- Un `README.md` expliquant son rôle
- Une documentation dans `docs/` si c'est un concept général
- Des commentaires dans le code pour les parties complexes

### 4. Structure modulaire et évolutive

- Chaque étape du projet a son dossier dans `charge_timeline/`
- Chaque service a son propre dossier à la racine
- La structure doit permettre l'ajout facile de nouveaux composants

## Checklist de vérification

### Avant chaque commit

- [ ] Aucun fichier sensible dans le staging
- [ ] `.gitignore` à jour
- [ ] Documentation mise à jour si nécessaire
- [ ] Structure respectée

### Lors de l'ajout d'un nouveau composant

- [ ] Créer le dossier avec structure appropriée
- [ ] Ajouter un `README.md`
- [ ] Mettre à jour le `README.md` principal
- [ ] Créer les fichiers `.example` pour la configuration
- [ ] Mettre à jour `.gitignore` si nécessaire

### Lors de la modification de la structure

- [ ] Documenter dans `docs/STRUCTURE.md`
- [ ] Vérifier l'impact sur les autres composants
- [ ] Mettre à jour les références dans la documentation

## Structure attendue

```
LIA/
├── README.md                    ✅ Présent
├── .gitignore                   ✅ Présent
├── env.example                  ✅ Présent
├── config/                      ✅ Présent
│   ├── api.conf.example         ✅ Présent
│   └── api.conf                 ⚠️ Non versionné (correct)
├── docs/                        ✅ Présent
│   ├── architecture.md          ✅ Présent
│   ├── CONTEXT.md               ✅ Présent
│   ├── STRUCTURE.md             ✅ Présent
│   └── ORGANISATION.md          ✅ Ce fichier
├── charge_timeline/             ✅ Présent
│   ├── etape1_cahier_charges/   ✅ Présent
│   ├── etape2_simulation_multiagent/  ✅ Présent
│   └── etape3_interface_supervision/  ✅ Présent
└── memory_service/              ✅ Présent
```

## Problèmes courants et solutions

### Problème : Fichier sensible versionné

**Solution** :
1. Retirer le fichier du dépôt : `git rm --cached fichier`
2. Ajouter au `.gitignore`
3. Créer un template `.example`
4. Régénérer le fichier réel localement

### Problème : Structure incohérente

**Solution** :
1. Identifier les fichiers mal placés
2. Les déplacer vers le bon emplacement
3. Mettre à jour les références
4. Documenter dans `docs/STRUCTURE.md`

### Problème : Documentation obsolète

**Solution** :
1. Identifier les sections obsolètes
2. Mettre à jour ou supprimer
3. Vérifier la cohérence avec le code
4. Ajouter des dates de dernière mise à jour si nécessaire

## Maintenance régulière

### Hebdomadaire

- Vérifier que les fichiers sensibles ne sont pas versionnés
- Vérifier la cohérence de la structure
- Nettoyer les fichiers temporaires

### Mensuel

- Réviser la documentation
- Vérifier que les README sont à jour
- Nettoyer les fichiers obsolètes

### Par étape du projet

- Mettre à jour le statut dans le README principal
- Documenter les changements structurels
- Créer les dossiers pour les prochaines étapes

## Commandes utiles

### Vérifier les fichiers sensibles

```bash
# Chercher les fichiers potentiellement sensibles
git ls-files | grep -E "(conf|secret|key|token|\.env|\.db)"

# Vérifier ce qui serait commité
git status
```

### Nettoyer les fichiers temporaires

```bash
# Supprimer les fichiers Python compilés
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Supprimer les fichiers de cache
find . -type d -name ".pytest_cache" -exec rm -r {} +
find . -type d -name ".cache" -exec rm -r {} +
```

## Contact et questions

Pour toute question sur l'organisation du workspace, consulter :
1. Ce document (`docs/ORGANISATION.md`)
2. La structure détaillée (`docs/STRUCTURE.md`)
3. Le README principal (`README.md`)



