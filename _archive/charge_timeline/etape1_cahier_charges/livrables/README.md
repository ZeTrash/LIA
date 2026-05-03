# Livrables Étape 1

Ce dossier regroupe les descriptions formelles promises pour la couche mémoire locale.

| Fichier | Description |
| --- | --- |
| `schema_memory_context.json` | JSON Schema de référence pour les paquets `GET /context`. |
| `schema_memory_context.sql` | Script SQL logique (SQLite) couvrant traits, souvenirs, interactions, gouvernance. |
| `api_spec_openapi.yaml` | Spécification OpenAPI 3.1 complète (endpoints, exemples, erreurs). |
| `architecture_persistance.md` | Choix techniques (persistance, sécurité, archivage) et organisation des fichiers. |
| `gouvernance_algorithmes.md` | Règles chiffrées (scoring, drift, purge, rollback) et pseudo-code opératoire. |
| `plan_tests_observabilite.md` | Plan de tests automatisés, KPI, dashboard et outillage d'observabilité. |
| `validation_SL1_SL4.md` | Tableau d'acceptation officiel des livrables SL1→SL4. |

**Note** : Le code exécutable du mock server se trouve dans `tools/mock_server/` (à la racine du projet), pas dans ce dossier de livrables.

Ces artefacts reprennent fidèlement le périmètre SL1→SL4 décrit dans `README.md` et peuvent être validés indépendamment.




