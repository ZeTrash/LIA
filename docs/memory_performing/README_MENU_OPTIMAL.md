# Menu Optimal - Documentation

**Date** : 2025-02-20  
**Statut** : 📋 En conception  
**Version** : 1.0

---

## Vue d'ensemble

Cette documentation décrit le **menu optimal** pour le système de planification cognitive de LIA, intégré avec MemoryRank V2.

## Documents disponibles

### 1. [Concept du Menu Optimal](CONCEPT_MENU_OPTIMAL.md)

Décrit les principes et concepts du menu optimal :
- Différences avec l'exemple initial
- Principes de conception
- Structure du menu
- Intégration avec MemoryRank V2
- Intégration avec le système de patterns V2 (Gemini/Groq)

### 2. [Architecture du Menu Optimal](ARCHITECTURE_MENU_OPTIMAL.md)

Décrit l'architecture technique :
- Composants principaux
- Structure des actions
- Flux de construction
- Intégration avec MemoryStore

### 3. [Intégration avec MemoryRank V2](INTEGRATION_MEMORY_MENU.md)

Décrit l'intégration technique :
- Points d'intégration
- Migration progressive
- Compatibilité
- Tests d'intégration

### 4. [Exemples d'utilisation](EXEMPLES_MENU_OPTIMAL.md)

Exemples concrets d'utilisation :
- Requête simple "Qui es-tu ?"
- Recherche sémantique
- Navigation dans le graphe
- Menu adaptatif
- Patterns adaptatifs

### 5. [Plan d'implémentation](PLAN_IMPLEMENTATION_MENU.md)

Plan détaillé d'implémentation :
- Phases d'implémentation
- Estimation
- Critères de succès
- Risques et mitigation

## Principes clés

### 1. Exploitation de MemoryRank

Le menu utilise les **scores MemoryRank** pour :
- Prioriser les informations importantes
- Suggérer des connexions pertinentes
- Filtrer le bruit

### 2. Navigation sémantique

Permet :
- Recherche par concept
- Exploration par liens
- Accès direct aux phrases importantes

### 3. Adaptation contextuelle

Le menu s'adapte selon :
- La requête utilisateur
- L'historique de la session
- Les patterns appris

## Structure du menu

### Niveau 0 : Menu de base
- Analyser la requête
- Rechercher dans la mémoire
- Consulter ma connaissance de moi-même
- Consulter les patterns
- Répondre

### Niveau 1 : Menu général
- Connaître mon identité
- Connaître mes traits
- Connaître mes capacités
- Consulter mes souvenirs
- Rechercher un concept
- Répondre
- Revenir

### Niveau 2 : Menu spécifique
- Souvenirs : Top, recherche, connexions, récents, par catégorie
- Identité/Traits/Capacités : Top, recherche, tous, connexions

## Intégration avec MemoryRank V2

Le menu optimal exploite :
- **Segmentation par phrases** : Recherche dans les phrases mémorisées
- **Scores MemoryRank** : Tri et priorisation
- **Graphe de liens** : Navigation dans les connexions
- **Filtrage sémantique** : Recherche intelligente

## Avantages

### Pour l'agent
- Accès rapide aux informations importantes
- Navigation efficace dans la mémoire structurée
- Décisions éclairées

### Pour le système
- Exploitation complète de MemoryRank V2
- Meilleure utilisation de la structure sémantique
- Patterns plus pertinents

### Pour l'utilisateur
- Réponses plus pertinentes
- Cohérence améliorée

## Statut actuel

- ✅ **Concept** : Défini
- ✅ **Architecture** : Définie
- ✅ **Plan d'implémentation** : Défini
- ⏳ **Implémentation** : À venir
- ⏳ **Tests** : À venir
- ⏳ **Documentation utilisateur** : À venir

## Prochaines étapes

1. **Révision** : Valider le concept et l'architecture
2. **Implémentation** : Commencer Phase 1 (Extension MemoryStore)
3. **Tests** : Valider chaque phase
4. **Documentation** : Finaliser la documentation utilisateur

## Références

- **MemoryRank V2** : `docs/memory_system/README.md`
- **Système de patterns V2** : `docs/memory_performing/SYSTEME_PATTERNS_V2.md`
- **Intégration Patterns + Menu** : `docs/memory_performing/INTEGRATION_PATTERNS_MENU.md`
- **Exemple initial** : `docs/memory_performing/exemple_process.md`

