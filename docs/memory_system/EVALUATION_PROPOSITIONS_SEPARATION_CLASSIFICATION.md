# Évaluation des Propositions : Séparation BD et Classification LLM

**Date** : 2024-12  
**Auteur** : Analyse technique  
**Statut** : 📋 Évaluation (non implémenté)

---

## Vue d'ensemble

Ce document évalue deux propositions pour améliorer le système de mémoire de LIA :

1. **Séparation de la base de données** : Créer deux BD distinctes (ou séparer en schémas) — une pour la mémoire de l'agent (LIA), une pour les utilisateurs.
2. **Classification LLM des phrases** : Ajouter un appel Groq/Gemini pour classifier chaque phrase à stocker par MemoryRank V2 dans la table correspondante.

---

## Proposition 1 : Séparation de la Base de Données

### Description

Actuellement, toutes les données mémoire sont stockées dans une seule base de données (`agent_memory.db`) :
- Traits de LIA (persona, skills, style)
- Souvenirs génériques (facts, preferences)
- Interactions utilisateur (logs)
- Patterns de menus
- Liens MemoryRank

**Proposition** : Séparer en deux bases distinctes :
- `agent_memory.db` : Mémoire de LIA uniquement (traits, souvenirs génériques, patterns)
- `user_memory.db` : Mémoire des utilisateurs (interactions, souvenirs utilisateur-spécifiques)

### Architecture Actuelle

```
agent_memory.db
├── traits (LIA uniquement)
├── souvenirs (mixte : LIA + utilisateurs)
├── interaction_logs (tous utilisateurs)
├── patterns (LIA)
├── theme_patterns (LIA)
└── memory_links (graphe mixte)
```

### Architecture Proposée

```
agent_memory.db                    user_memory.db
├── traits (LIA)                   ├── user_traits (par user_id)
├── souvenirs (LIA uniquement)     ├── user_memories (par user_id)
├── patterns (LIA)                 ├── user_interactions (par user_id)
├── theme_patterns (LIA)           └── user_memory_links (graphe par user)
└── agent_memory_links (LIA)
```

### Avantages ✅

1. **Isolation claire** : Séparation nette entre mémoire agent vs utilisateurs
2. **Sécurité/privacy** : Plus facile de gérer la suppression/anonymisation des données utilisateur
3. **Performance** : Requêtes plus ciblées (pas besoin de filtrer par `user_id` partout)
4. **Scalabilité** : Possibilité de déplacer `user_memory.db` sur un serveur séparé
5. **Maintenance** : Backup/restauration indépendants
6. **Conformité RGPD** : Plus simple de répondre à une demande de suppression utilisateur

### Inconvénients ❌

1. **Complexité** : Deux instances `Database` à gérer, deux sessions SQLAlchemy
2. **Requêtes croisées** : Si besoin de corréler données agent ↔ utilisateur, requêtes plus complexes
3. **MemoryRank** : Le graphe MemoryRank devient fragmenté (agent vs utilisateur) — perte de liens transversaux
4. **Migration** : Nécessite une migration des données existantes
5. **Code dupliqué** : Logique de stockage/récupération à dupliquer ou abstraire
6. **Synchronisation** : Si besoin de synchroniser certaines données (ex: patterns utilisés par plusieurs users)

### Analyse Technique

#### Impact sur le Code

**Fichiers à modifier** :
- `memory_service/db.py` : Créer `UserDatabase` ou ajouter paramètre `db_type`
- `memory_service/store.py` : Adapter `MemoryStore` pour gérer deux BD
- `memory_service/models.py` : Possiblement dupliquer les modèles ou ajouter `user_id` partout
- `core/llm_adapter.py` : Adapter l'initialisation
- `interfaces/user_channel.py` : Passer `user_id` dans les appels mémoire

**Complexité estimée** : 🔴 **Moyenne à élevée** (2-3 jours de dev + tests)

#### Alternative : Séparation par Schéma/Tables

Au lieu de deux BD, utiliser une seule BD avec :
- Tables préfixées : `agent_traits`, `user_traits`, `agent_souvenirs`, `user_souvenirs`
- Colonne `user_id` dans toutes les tables utilisateur
- Index sur `user_id` pour performance

**Avantage** : Moins de complexité, requêtes croisées possibles  
**Inconvénient** : Moins d'isolation, toujours une seule BD à gérer

### Recommandation

**✅ APPROUVER avec nuance** :

1. **Court terme** : Ajouter une colonne `user_id` dans les tables existantes (`souvenirs`, `interaction_logs`) pour isoler les données utilisateur au niveau SQL
2. **Moyen terme** : Si besoin de scalabilité/privacy, migrer vers deux BD distinctes
3. **Compromis** : Utiliser une seule BD mais avec schémas/tables séparés (`agent_*` vs `user_*`)

**Raison** : La séparation complète est utile mais coûteuse. Commencer par l'isolation via `user_id` permet de tester sans refonte majeure.

---

## Proposition 2 : Classification LLM des Phrases dans les Tables Appropriées

### Description

**Problème actuel** : Toutes les phrases importantes sont stockées dans la table `souvenirs` via `add_memory()`, même si elles devraient aller dans d'autres tables :
- "Je m'appelle ZeTrash" → devrait aller dans `traits` (trait `nom_utilisateur`)
- "Connaitre mon identité" → ne devrait PAS être stocké comme souvenir (c'est une action interne)
- "J'aime Python" → peut aller dans `souvenirs` avec catégorie `preference`

**Exemple concret du problème** :
```
Requête : "Que connais-tu de moi ?"
Résultat actuel :
  - "Connaitre mon identité" → stocké dans souvenirs (❌ incorrect)
  - "Consulter ma mémoire" → stocké dans souvenirs (❌ incorrect)
  
Ces phrases sont des actions internes, pas des souvenirs à mémoriser !
```

**Ce qui devrait se passer** :
```
Phrase : "Je m'appelle ZeTrash"
→ Classification LLM : table="traits", fields={type="user_info", label="nom_utilisateur", value="ZeTrash"}
→ Stockage : add_trait() dans la table traits ✅

Phrase : "J'aime Python"
→ Classification LLM : table="souvenirs", category="preference"
→ Stockage : add_memory() dans la table souvenirs ✅

Phrase : "Connaitre mon identité" (action interne)
→ Classification LLM : table="none" ou "skip"
→ Pas de stockage (c'est une action, pas une information) ✅
```

Actuellement, `PhraseMemoryProcessor` utilise une catégorisation heuristique simple (`_categorize_phrase`) qui ne fait que déterminer la catégorie (`preference` vs `fact`), mais **tout va quand même dans `souvenirs`**.

**Proposition** : Ajouter un appel Groq/Gemini pour classifier chaque phrase importante avant stockage :
- Envoyer la structure complète de la BD (toutes les tables disponibles : `traits`, `souvenirs`, `interaction_logs`, etc.)
- Demander à l'LLM de choisir dans quelle **TABLE** stocker la phrase
- Si nécessaire, permettre à l'LLM de proposer une nouvelle table (comme pour `theme_patterns`)
- Stocker dans la table correspondante avec les champs appropriés

### Architecture Actuelle

```python
# Dans PhraseMemoryProcessor._store_phrase()
# TOUJOURS stocke dans souvenirs, peu importe la catégorie
category = self._categorize_phrase(phrase_text)  # "preference" ou "fact"
memory_id = self.store.add_memory(  # ← TOUJOURS add_memory()
    category=category,
    content=phrase_text,
    ...
)

# Problème : "Je m'appelle ZeTrash" va dans souvenirs au lieu de traits
```

### Architecture Proposée

```python
# Nouveau : Classification LLM pour déterminer la TABLE
async def classify_phrase_table_with_llm(
    phrase: str, 
    db_schema: Dict,
    existing_tables: List[str]
) -> Dict[str, Any]:
    """
    Retourne :
    {
        "table": "traits" | "souvenirs" | "interaction_logs" | "nouvelle_table",
        "table_name": "user_identity" (si nouvelle table),
        "fields": {...} (champs à remplir selon la table)
    }
    """
    prompt = f"""
    Structure de la BD disponible :
    {db_schema}
    
    Tables existantes : {existing_tables}
    
    Phrase à classifier : "{phrase}"
    
    Choisis :
    1. La TABLE appropriée (traits, souvenirs, interaction_logs, ou propose une nouvelle table)
    2. Si nouvelle table, propose un nom descriptif
    3. Les champs à remplir selon le schéma de la table
    
    Format JSON :
    {{
        "table": "traits",
        "fields": {{
            "type": "user_info",
            "label": "nom_utilisateur",
            "value": "ZeTrash"
        }}
    }}
    """
    result = await groq_adapter.query(prompt)
    return parse_json_response(result)

# Utilisation dans _store_phrase()
classification = await self.classify_phrase_table_with_llm(...)
if classification["table"] == "traits":
    trait_id = self.store.add_trait(**classification["fields"])
elif classification["table"] == "souvenirs":
    memory_id = self.store.add_memory(**classification["fields"])
elif classification["table"] == "nouvelle_table":
    # Créer la nouvelle table dynamiquement (comme theme_patterns)
    self._create_dynamic_table(classification["table_name"], classification["fields"])
```

### Avantages ✅

1. **Précision** : Classification contextuelle dans la bonne table au lieu de tout mettre dans `souvenirs`
2. **Flexibilité** : Peut détecter des patterns complexes ("Je m'appelle X" → `traits` avec `label="nom_utilisateur"`)
3. **Évolutivité** : Facile d'ajouter de nouvelles tables sans modifier le code (comme `theme_patterns`)
4. **Nuance** : Distinction fine entre ce qui doit aller dans `traits` vs `souvenirs` vs `interaction_logs`
5. **Extraction structurée** : Possibilité d'extraire des entités structurées (nom, préférence, fait) directement dans les bons champs
6. **Résolution du problème actuel** : Les phrases comme "Connaitre mon identité" ne seront plus stockées comme souvenirs
7. **Création dynamique** : Le modèle peut créer de nouvelles tables si nécessaire (ex: `user_preferences`, `user_goals`)

### Inconvénients ❌

1. **Latence** : Ajout d'un appel API externe par phrase importante (peut ralentir le traitement)
2. **Coût** : Consommation de tokens Groq/Gemini à chaque classification
3. **Fiabilité** : Dépendance à un service externe (peut échouer)
4. **Complexité** : Gestion d'erreurs, retry, fallback nécessaire
5. **Overhead** : Pour des phrases simples, la heuristique suffit peut-être
6. **Rate limiting** : Risque de dépasser les limites API si beaucoup de phrases

### Analyse Technique

#### Impact sur le Code

**Fichiers à modifier** :
- `memory_service/phrase_memory_processor.py` : 
  - Ajouter méthode `_classify_table_with_llm()` pour déterminer la table
  - Modifier `_store_phrase()` pour utiliser la bonne méthode selon la table (`add_trait()` vs `add_memory()`)
  - Ajouter méthode `_create_dynamic_table()` pour créer de nouvelles tables si nécessaire
- `memory_service/store.py` : 
  - Adapter pour supporter création dynamique de tables
  - Ajouter méthode générique pour stocker selon classification
- `memory_service/models.py` : 
  - Créer système de modèles dynamiques (comme `ThemePatternModel` mais générique)
- `core/llm_adapter.py` : Passer `groq_adapter` au `PhraseMemoryProcessor`

**Complexité estimée** : 🟡 **Moyenne** (1-2 jours de dev + tests)

#### Optimisations Possibles

1. **Cache** : Mémoriser les classifications similaires pour éviter appels redondants
2. **Batch** : Classifier plusieurs phrases en un seul appel (format JSON array)
3. **Fallback** : Utiliser heuristique si LLM indisponible (défaut : `souvenirs` avec catégorie)
4. **Seuil** : Ne classifier que les phrases avec score d'importance élevé (>0.6)
5. **Asynchrone** : Classifier en arrière-plan après stockage initial (ne pas bloquer le flux)
6. **Patterns pré-appris** : Mémoriser les patterns fréquents ("Je m'appelle X" → toujours `traits`)
7. **Validation** : Vérifier que la table proposée existe avant de créer une nouvelle

### Recommandation

**✅ APPROUVER avec optimisations** :

1. **Hybride** : Utiliser LLM pour les phrases à score élevé (>0.6), heuristique pour le reste
2. **Batch** : Classifier par batch de 5-10 phrases pour réduire appels API
3. **Cache** : Mémoriser classifications pour phrases similaires (pattern matching)
4. **Fallback robuste** : Heuristique si LLM indisponible (défaut : `souvenirs`)
5. **Asynchrone** : Classifier après stockage initial (ne pas bloquer le flux)
6. **Création dynamique** : Permettre création de nouvelles tables comme pour `theme_patterns`
7. **Validation** : Vérifier que la table existe avant création, valider le schéma proposé

**Raison** : Cette proposition résout directement le problème actuel (phrases mal classées) et permet une évolution dynamique du schéma de BD, similaire au système de `theme_patterns`. L'impact sur la latence peut être minimisé avec batch + cache + asynchrone.

---

## Synthèse et Recommandations Finales

### Priorité d'Implémentation

1. **🔴 Priorité 1** : Classification LLM (Proposition 2) — Impact immédiat sur la qualité
2. **🟡 Priorité 2** : Isolation par `user_id` (Proposition 1, version simplifiée) — Préparation pour scalabilité
3. **🟢 Priorité 3** : Séparation complète BD (Proposition 1, version complète) — Si besoin de privacy/scalabilité

### Plan d'Action Recommandé

#### Phase 1 : Classification LLM dans Tables Appropriées (2-3 semaines)
- [ ] Ajouter méthode `_classify_table_with_llm()` dans `PhraseMemoryProcessor`
- [ ] Modifier `_store_phrase()` pour router vers `add_trait()` ou `add_memory()` selon classification
- [ ] Implémenter batch classification (5-10 phrases en JSON array)
- [ ] Ajouter cache de classifications (patterns fréquents)
- [ ] Fallback sur heuristique si LLM indisponible (défaut : `souvenirs`)
- [ ] Système de création dynamique de tables (comme `theme_patterns`)
- [ ] Tests unitaires et intégration
- [ ] Migration des données existantes mal classées

#### Phase 2 : Isolation Utilisateur (2-3 semaines)
- [ ] Ajouter colonne `user_id` dans `souvenirs` et `interaction_logs`
- [ ] Adapter `MemoryStore` pour filtrer par `user_id`
- [ ] Migration des données existantes
- [ ] Tests de performance et isolation

#### Phase 3 : Séparation BD (optionnel, 3-4 semaines)
- [ ] Créer `UserDatabase` séparée
- [ ] Migrer données utilisateur
- [ ] Adapter code pour gérer deux BD
- [ ] Tests de migration et rollback

### Considérations Additionnelles

1. **Performance** : Mesurer l'impact de la classification LLM sur la latence
2. **Coût** : Estimer consommation API Groq/Gemini mensuelle
3. **Monitoring** : Ajouter métriques pour taux de classification, erreurs LLM
4. **Documentation** : Documenter les nouvelles catégories et leur usage

---

## Conclusion

Les deux propositions sont **valides et amélioreraient le système**, mais avec des priorités différentes :

- **Classification LLM** : Impact immédiat sur la qualité de mémorisation → **À implémenter en priorité**
- **Séparation BD** : Utile pour scalabilité/privacy → **À faire progressivement** (d'abord isolation, puis séparation complète si besoin)

L'approche recommandée est **incrémentale** : améliorer la classification d'abord, puis isoler les données utilisateur, et enfin séparer complètement si nécessaire.

