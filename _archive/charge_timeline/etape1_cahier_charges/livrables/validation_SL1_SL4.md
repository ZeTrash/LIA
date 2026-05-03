# Validation des livrables SL1 → SL4

| Sous-lot | Livrables formels | Référence fichier | Statut | Notes de validation |
| --- | --- | --- | --- | --- |
| SL1 – Modèle de données | JSON Schema, DDL SQL, dictionnaire | `schema_memory_context.json`, `schema_memory_context.sql`, `README.md` (section tableau) | ✅ Validé | Schéma et DDL alignés, TTL/index figés, cohérence contrôlée. |
| SL2 – Service mémoire | Spécification API complète + exemples | `api_spec_openapi.yaml` | ✅ Validé | Contrats GET/POST définis, erreurs normalisées, mock prêt. |
| SL3 – Gouvernance & scoring | Règles chiffrées + pseudo-code | `gouvernance_algorithmes.md` | ✅ Validé | Poids, demi-vies, seuils drift/purge explicités, rollback décrit. |
| SL4 – Observabilité | Plan de tests, KPI, outillage | `plan_tests_observabilite.md`, `architecture_persistance.md` (section dashboard) | ✅ Validé | Formats CSV/Prom prometheus, scripts planifiés, SLA test listés. |

Validation effectuée le 2024-12-07. Toute évolution devra être tracée via ce tableau.




