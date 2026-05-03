# Concept du Menu Optimal - Intégration MemoryRank V2

**Date** : 2025-02-20  
**Statut** : 📋 En conception  
**Version** : 1.0

---

## Vue d'ensemble

Ce document définit le concept d'un **menu optimal** pour le système de planification cognitive de LIA, adapté au système de mémoire MemoryRank V2 qui traite les interactions par **unités sémantiques** (phrases) plutôt que par prompts bruts.

## Principe fondamental

> **Un menu optimal exploite la structure sémantique de la mémoire pour guider efficacement l'agent vers les informations pertinentes.**

## Différences avec l'exemple initial

### Exemple initial (`exemple_process.md`)
- Menu hiérarchique simple (base → général → spécifique)
- Actions génériques (consulter identité, traits, mémoire)
- Pas d'exploitation de la structure MemoryRank V2
- Patterns appris de manière linéaire

### Menu optimal (ce document)
- **Exploitation de MemoryRank** : Utilise les scores de centralité pour prioriser les informations
- **Navigation sémantique** : Accès direct aux phrases/concepts importants
- **Recherche contextuelle** : Recherche dans la mémoire basée sur la requête utilisateur
- **Patterns adaptatifs** : Patterns qui s'adaptent à la structure de la mémoire
- **Filtrage intelligent** : Menu adapté selon le contexte et l'historique

## Principes de conception

### 1. Exploitation de la structure MemoryRank

Le menu doit exploiter les **scores MemoryRank** pour :
- **Prioriser les informations** : Afficher d'abord les souvenirs/phrases les plus importants
- **Suggérer des connexions** : Proposer des souvenirs liés aux concepts centraux
- **Filtrer le bruit** : Masquer les informations peu importantes sauf demande explicite

### 2. Navigation sémantique

Au lieu de naviguer par catégories fixes (identité, traits, mémoire), le menu doit permettre :
- **Recherche par concept** : "Trouver des informations sur Python"
- **Exploration par liens** : "Voir les souvenirs liés à ce concept"
- **Accès direct aux phrases importantes** : "Afficher les phrases les plus centrales"

### 3. Adaptation contextuelle

Le menu doit s'adapter selon :
- **La requête utilisateur** : Proposer des actions pertinentes au contexte
- **L'historique de la session** : Éviter de proposer des actions déjà effectuées
- **Les patterns appris** : Utiliser les patterns pour suggérer des séquences optimales

### 4. Hiérarchie flexible

La hiérarchie menu doit être :
- **Profondeur variable** : Permettre d'accéder rapidement aux informations sans navigation excessive
- **Raccourcis intelligents** : Actions fréquentes accessibles directement
- **Navigation arrière** : Toujours possible de revenir en arrière ou changer de direction

## Structure du menu optimal

### Niveau 0 : Menu de base (contexte initial)

Actions disponibles :
1. **Analyser la requête utilisateur** (B1)
   - Afficher la requête et suggérer des actions pertinentes
   
2. **Rechercher dans la mémoire** (B2)
   - Recherche sémantique directe dans les phrases mémorisées
   - Utilise MemoryRank pour prioriser les résultats
   
3. **Consulter ma connaissance de moi-même** (B3)
   - Menu général (identité, traits, capacités, souvenirs)
   
4. **Consulter les patterns préférés** (B4) - Optionnel
   - Afficher les patterns appris pour ce type de requête
   
5. **Répondre à la requête** (B5)
   - Action finale pour générer la réponse

### Niveau 1 : Menu général (connaissance de soi)

Actions disponibles :
1. **Connaître mon identité** (G1)
   - Afficher les phrases d'identité les plus importantes (triées par MemoryRank)
   
2. **Connaître mes traits** (G2)
   - Afficher les traits les plus centraux (triés par MemoryRank)
   - Option : Filtrer par type (personnalité, style, relation)
   
3. **Connaître mes capacités** (G3)
   - Afficher les capacités mémorisées (triées par MemoryRank)
   
4. **Consulter mes souvenirs** (G4)
   - Menu spécifique pour explorer la mémoire
   
5. **Rechercher un concept spécifique** (G5)
   - Recherche sémantique dans toute la mémoire
   
6. **Répondre à la requête** (G5)
   - Action finale
   
7. **Revenir au menu précédent** (G6)

### Niveau 2 : Menu spécifique - Souvenirs

Actions disponibles :
1. **Voir les souvenirs les plus importants** (S1)
   - Top N souvenirs triés par MemoryRank
   - Afficher les phrases centrales
   
2. **Rechercher par concept** (S2)
   - Recherche sémantique dans les souvenirs
   - Résultats triés par pertinence + MemoryRank
   
3. **Explorer les connexions** (S3)
   - Pour un souvenir donné, voir les souvenirs liés
   - Navigation dans le graphe MemoryRank
   
4. **Voir les souvenirs récents** (S4)
   - Derniers souvenirs ajoutés (avec filtrage par importance)
   
5. **Voir les souvenirs par catégorie** (S5)
   - Filtrer par catégorie (fact, preference, event, etc.)
   - Tri par MemoryRank dans chaque catégorie
   
6. **Répondre à la requête** (S6)
   
7. **Revenir au menu précédent** (S7)

### Niveau 2 : Menu spécifique - Identité/Traits/Capacités

Actions disponibles :
1. **Voir les plus importants** (I1/T1/C1)
   - Top N éléments triés par MemoryRank
   
2. **Rechercher un élément spécifique** (I2/T2/C2)
   - Recherche par label ou contenu
   
3. **Voir tous les éléments** (I3/T3/C3)
   - Liste complète triée par MemoryRank
   
4. **Voir les éléments liés** (I4/T4/C4)
   - Pour un élément donné, voir les éléments liés dans le graphe
   
5. **Répondre à la requête** (I5/T5/C5)
   
6. **Revenir au menu précédent** (I6/T6/C6)

## Intégration avec MemoryRank V2

### Utilisation des scores MemoryRank

Chaque action qui affiche des informations doit :
1. **Récupérer les éléments** depuis la mémoire
2. **Trier par MemoryRank** (score `memory_rank_score`)
3. **Afficher les plus importants en premier**
4. **Suggérer des connexions** via les liens MemoryRank

### Recherche sémantique

La recherche doit :
1. **Segmenter la requête** en phrases (comme MemoryRank V2)
2. **Comparer avec les phrases mémorisées** (similarité sémantique)
3. **Pondérer par MemoryRank** : `score_final = α·similarité + β·memory_rank`
4. **Retourner les résultats triés**

### Navigation dans le graphe

Pour l'action "Explorer les connexions" :
1. **Récupérer les liens** du souvenir actuel
2. **Trier les souvenirs liés** par poids de lien + MemoryRank
3. **Afficher les connexions les plus importantes**
4. **Permettre la navigation** vers les souvenirs liés

## Patterns adaptatifs

### Intégration avec le système de patterns V2

Le menu optimal **utilise DIRECTEMENT le système de patterns V2** (classifiés par Gemini/Groq) pour déterminer automatiquement les actions :

1. **Classification du thème** (avant la planification) :
   - Gemini/Groq classe la requête dans un thème (ex: "identité", "mémoire", "salutation")
   - Les patterns sont filtrés par ce thème pour des décisions plus précises

2. **Utilisation automatique des patterns** :
   - Le `PatternLearner` récupère l'action recommandée depuis la mémoire (patterns stockés)
   - **L'agent local n'est PAS consulté** pour choisir dans les menus (mode `LIA_PATTERNS_ONLY=1` par défaut)
   - L'action déterminée par le pattern est exécutée automatiquement
   - Fallback sûr si aucun pattern disponible (généralement RESPOND)

3. **Apprentissage après interaction** :
   - Après chaque réponse finale, Gemini/Groq analyse la séquence d'actions exécutée automatiquement
   - Suggère la séquence optimale au format `{{theme_pattern},{B2, G3, G5}}`
   - Les patterns sont mis à jour dans la base de données pour les prochaines requêtes

**Voir** : `INTEGRATION_PATTERNS_MENU.md` pour les détails techniques.

### Patterns basés sur MemoryRank

Les patterns appris doivent prendre en compte :
- **Les concepts centraux** : Si un concept a un MemoryRank élevé, il est probablement important
- **Les connexions fréquentes** : Si deux concepts sont souvent liés, suggérer cette connexion
- **Le contexte sémantique** : Patterns différents selon le type de requête

### Apprentissage amélioré

L'apprentissage de patterns doit :
1. **Enregistrer les séquences d'actions** comme avant
2. **Enrichir avec le contexte MemoryRank** : Quels souvenirs ont été consultés ?
3. **Apprendre les patterns de navigation** : Quelles connexions sont souvent explorées ?
4. **Adapter selon la structure** : Patterns différents si la mémoire est dense vs sparse
5. **Utiliser Gemini/Groq** : Source externe fiable pour l'apprentissage optimal

## Avantages du menu optimal

### Pour l'agent
- **Accès rapide** aux informations importantes
- **Navigation efficace** dans la mémoire structurée
- **Décisions éclairées** basées sur l'importance des informations

### Pour le système
- **Exploitation complète** de MemoryRank V2
- **Meilleure utilisation** de la structure sémantique
- **Patterns plus pertinents** basés sur la structure réelle

### Pour l'utilisateur
- **Réponses plus pertinentes** car l'agent accède aux bonnes informations
- **Cohérence améliorée** grâce à l'exploitation de la mémoire structurée

## Prochaines étapes

1. **Architecture détaillée** : Voir `ARCHITECTURE_MENU_OPTIMAL.md`
2. **Intégration technique** : Voir `INTEGRATION_MEMORY_MENU.md`
3. **Exemples concrets** : Voir `EXEMPLES_MENU_OPTIMAL.md`
4. **Plan d'implémentation** : Voir `PLAN_IMPLEMENTATION_MENU.md`

