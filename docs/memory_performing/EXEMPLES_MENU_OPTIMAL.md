# Exemples d'utilisation du Menu Optimal

**Date** : 2025-02-20  
**Statut** : 📋 En conception  
**Version** : 1.0

---

## Vue d'ensemble

Ce document présente des exemples concrets d'utilisation du menu optimal avec MemoryRank V2.

## Exemple 1 : Requête simple "Qui es-tu ?"

### Contexte
- Requête utilisateur : "Qui es-tu ?"
- État initial : Menu de base
- Mémoire : Identité, traits, capacités déjà mémorisés avec MemoryRank

### Flux d'exécution

#### Itération 1 : Menu de base

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
1. Analyser la requête utilisateur (B1)
2. Rechercher dans la mémoire (B2) [Pertinence: 0.8]
3. Consulter ma connaissance de moi-même (B3) [Pertinence: 0.9]
4. Répondre à la requête (B5)

=== RECOMMANDATION ===
Le choix recommandé est 3 (Consulter ma connaissance de moi-même),
mais vous pouvez choisir une autre option.
```

**Choix de l'agent** : 3 (B3)

**Résultat** : Passage au menu général

#### Itération 2 : Menu général

**Menu proposé** :
```
=== HISTORIQUE INTERNE ===
Vous avez choisi de consulter votre connaissance de vous-même.

=== MENU D'ACTIONS INTERNES ===
1. Connaître mon identité (G1) [3 éléments disponibles, top: "Je suis LIA, un assistant IA..."]
2. Connaître mes traits (G2) [5 éléments disponibles, top: "Style de Réponse: professionnel"]
3. Connaître mes capacités (G3) [2 éléments disponibles]
4. Consulter mes souvenirs (G4) [Menu spécifique]
5. Rechercher un concept spécifique (G5)
6. Répondre à la requête (G6)
7. Revenir au menu précédent (G7)

=== RECOMMANDATION ===
Le choix recommandé est 1 (Connaître mon identité),
mais vous pouvez choisir une autre option.
```

**Choix de l'agent** : 1 (G1)

**Résultat** : Affichage des phrases d'identité les plus importantes

#### Itération 3 : Affichage identité

**Résultat de l'action** :
```
=== IDENTITÉ (triée par MemoryRank) ===

1. "Je suis LIA, un assistant IA autonome conçu pour aider les utilisateurs."
   [MemoryRank: 0.85, Connexions: 12]

2. "Mon objectif est de fournir des réponses pertinentes et utiles."
   [MemoryRank: 0.72, Connexions: 8]

3. "Je possède un système de mémoire qui me permet d'apprendre et de m'adapter."
   [MemoryRank: 0.68, Connexions: 6]

=== MENU D'ACTIONS INTERNES ===
1. Voir toutes les phrases d'identité (I3)
2. Explorer les connexions de la phrase 1 (I4)
3. Rechercher une phrase spécifique (I2)
4. Répondre à la requête (I5)
5. Revenir au menu précédent (I6)

=== RECOMMANDATION ===
Le choix recommandé est 4 (Répondre à la requête),
mais vous pouvez choisir une autre option.
```

**Choix de l'agent** : 4 (I5)

**Résultat** : Génération de la réponse finale

#### Réponse finale

```
Je suis LIA, un assistant IA autonome conçu pour aider les utilisateurs. 
Mon objectif est de fournir des réponses pertinentes et utiles. 
Je possède un système de mémoire qui me permet d'apprendre et de m'adapter 
à vos besoins au fil du temps.
```

## Exemple 2 : Recherche sémantique "Python"

### Contexte
- Requête utilisateur : "Qu'est-ce que tu sais sur Python ?"
- État initial : Menu de base
- Mémoire : Plusieurs souvenirs sur Python avec MemoryRank variés

### Flux d'exécution

#### Itération 1 : Menu de base

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
1. Analyser la requête utilisateur (B1)
2. Rechercher dans la mémoire (B2) [Pertinence: 0.95, "Python" détecté]
3. Consulter ma connaissance de moi-même (B3)
4. Répondre à la requête (B5)

=== RECOMMANDATION ===
Le choix recommandé est 2 (Rechercher dans la mémoire),
mais vous pouvez choisir une autre option.
```

**Choix de l'agent** : 2 (B2)

**Résultat** : Recherche sémantique dans la mémoire

#### Itération 2 : Résultats de recherche

**Résultat de l'action** :
```
=== RECHERCHE SÉMANTIQUE : "Python" ===

Résultats (triés par pertinence + MemoryRank) :

1. "Je préfère Python à Java pour le développement."
   [Score: 0.92, Similarité: 0.85, MemoryRank: 0.75, Catégorie: preference]

2. "Python est un langage de programmation que j'utilise souvent."
   [Score: 0.88, Similarité: 0.80, MemoryRank: 0.70, Catégorie: fact]

3. "J'ai aidé un utilisateur à créer un script Python pour automatiser des tâches."
   [Score: 0.82, Similarité: 0.75, MemoryRank: 0.65, Catégorie: event]

4. "Les bibliothèques Python comme pandas sont très utiles pour l'analyse de données."
   [Score: 0.78, Similarité: 0.70, MemoryRank: 0.60, Catégorie: fact]

=== MENU D'ACTIONS INTERNES ===
1. Explorer les connexions du résultat 1 (B2.1)
2. Voir plus de résultats (B2.2)
3. Rechercher un autre concept (B2.3)
4. Répondre à la requête (B5)
5. Revenir au menu précédent (B6)

=== RECOMMANDATION ===
Le choix recommandé est 4 (Répondre à la requête),
mais vous pouvez choisir une autre option.
```

**Choix de l'agent** : 4 (B5)

**Résultat** : Génération de la réponse finale

#### Réponse finale

```
D'après ma mémoire, je préfère Python à Java pour le développement. 
Python est un langage de programmation que j'utilise souvent, et j'ai 
déjà aidé des utilisateurs à créer des scripts Python pour automatiser 
des tâches. Les bibliothèques Python comme pandas sont très utiles pour 
l'analyse de données.
```

## Exemple 3 : Navigation dans le graphe

### Contexte
- Requête utilisateur : "Parle-moi de tes projets d'IA"
- État initial : Menu de base
- Mémoire : Souvenirs liés sur projets, IA, apprentissage

### Flux d'exécution

#### Itération 1 : Menu de base → Recherche

**Choix** : B2 (Rechercher dans la mémoire)

**Résultat** : Recherche "projets IA"

#### Itération 2 : Résultats de recherche

**Résultat** :
```
=== RECHERCHE SÉMANTIQUE : "projets IA" ===

1. "J'ai travaillé sur un système de mémoire pour agents autonomes."
   [Score: 0.90, MemoryRank: 0.80, Connexions: 5]
```

**Choix** : B2.1 (Explorer les connexions)

#### Itération 3 : Exploration des connexions

**Résultat de l'action** :
```
=== CONNEXIONS DU SOUVENIR ===
Souvenir: "J'ai travaillé sur un système de mémoire pour agents autonomes."
[MemoryRank: 0.80]

=== SOUVENIRS LIÉS (triés par poids de lien + MemoryRank) ===

1. "Le système MemoryRank utilise PageRank pour calculer l'importance."
   [Lien: causal, Poids: 0.9, MemoryRank: 0.75]

2. "J'ai implémenté la segmentation par phrases pour optimiser la mémoire."
   [Lien: causal, Poids: 0.85, MemoryRank: 0.70]

3. "Les patterns appris permettent d'améliorer les décisions."
   [Lien: cooccurrence, Poids: 0.7, MemoryRank: 0.65]

4. "L'apprentissage par renforcement guide le filtrage sémantique."
   [Lien: similarity, Poids: 0.6, MemoryRank: 0.60]

=== MENU D'ACTIONS INTERNES ===
1. Explorer les connexions du souvenir 1 (B2.1.1)
2. Voir le souvenir 1 en détail (B2.1.2)
3. Revenir aux résultats de recherche (B2.1.3)
4. Répondre à la requête (B5)
5. Revenir au menu précédent (B6)

=== RECOMMANDATION ===
Le choix recommandé est 4 (Répondre à la requête),
mais vous pouvez choisir une autre option.
```

**Choix** : 4 (B5)

**Résultat** : Génération de la réponse avec contexte enrichi

#### Réponse finale

```
J'ai travaillé sur un système de mémoire pour agents autonomes. Ce système 
utilise PageRank (MemoryRank) pour calculer l'importance des souvenirs. 
J'ai implémenté la segmentation par phrases pour optimiser la mémoire, et 
les patterns appris permettent d'améliorer les décisions. L'apprentissage 
par renforcement guide également le filtrage sémantique.
```

## Exemple 4 : Menu adaptatif selon contexte

### Contexte
- Requête utilisateur : "Quels sont tes traits les plus importants ?"
- État initial : Menu de base
- Mémoire : Plusieurs traits avec MemoryRank variés

### Flux d'exécution

#### Itération 1 : Menu de base

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
1. Analyser la requête utilisateur (B1)
2. Rechercher dans la mémoire (B2) [Pertinence: 0.7]
3. Consulter ma connaissance de moi-même (B3) [Pertinence: 0.95, "traits" détecté]
4. Répondre à la requête (B5)

=== RECOMMANDATION ===
Le choix recommandé est 3 (Consulter ma connaissance de moi-même),
mais vous pouvez choisir une autre option.
```

**Choix** : 3 (B3)

#### Itération 2 : Menu général (adapté)

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
1. Connaître mon identité (G1)
2. Connaître mes traits (G2) [Pertinence: 0.95, 5 éléments disponibles]
   Top 3: "Style de Réponse: professionnel" (0.85), 
          "Relation à l'utilisateur: bienveillant" (0.78),
          "Capacités Cognitives: analytique" (0.72)
3. Connaître mes capacités (G3)
4. Consulter mes souvenirs (G4)
5. Rechercher un concept spécifique (G5)
6. Répondre à la requête (G6)
7. Revenir au menu précédent (G7)

=== RECOMMANDATION ===
Le choix recommandé est 2 (Connaître mes traits),
mais vous pouvez choisir une autre option.
```

**Choix** : 2 (G2)

#### Itération 3 : Affichage traits (top par MemoryRank)

**Résultat de l'action** :
```
=== TRAITS (triés par MemoryRank) ===

1. Style de Réponse: professionnel
   [MemoryRank: 0.85, Poids: 5.0, Type: persona]
   "Je réponds de manière professionnelle et structurée."

2. Relation à l'utilisateur: bienveillant
   [MemoryRank: 0.78, Poids: 4.5, Type: persona]
   "Je cherche à aider l'utilisateur de manière bienveillante."

3. Capacités Cognitives: analytique
   [MemoryRank: 0.72, Poids: 4.0, Type: skill]
   "J'analyse les problèmes de manière méthodique."

4. Style de Communication: clair
   [MemoryRank: 0.65, Poids: 3.5, Type: persona]
   "Je communique de manière claire et concise."

5. Approche: adaptative
   [MemoryRank: 0.58, Poids: 3.0, Type: persona]
   "Je m'adapte au contexte et aux besoins de l'utilisateur."

=== MENU D'ACTIONS INTERNES ===
1. Voir tous les traits (T3)
2. Filtrer par type (T2)
3. Explorer les connexions du trait 1 (T4)
4. Répondre à la requête (T5)
5. Revenir au menu précédent (T6)

=== RECOMMANDATION ===
Le choix recommandé est 4 (Répondre à la requête),
mais vous pouvez choisir une autre option.
```

**Choix** : 4 (T5)

#### Réponse finale

```
Mes traits les plus importants sont :

1. **Style de Réponse : professionnel** - Je réponds de manière 
   professionnelle et structurée.

2. **Relation à l'utilisateur : bienveillant** - Je cherche à aider 
   l'utilisateur de manière bienveillante.

3. **Capacités Cognitives : analytique** - J'analyse les problèmes de 
   manière méthodique.

4. **Style de Communication : clair** - Je communique de manière claire 
   et concise.

5. **Approche : adaptative** - Je m'adapte au contexte et aux besoins 
   de l'utilisateur.
```

## Exemple 5 : Pattern adaptatif

### Contexte
- Requête utilisateur : "Rappelle-moi ce qu'on a discuté hier"
- État initial : Menu de base
- Patterns appris : Pour "rappelle-moi", pattern recommandé = B2 → G4 → S4

### Flux d'exécution

#### Itération 1 : Menu de base (avec pattern)

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
1. Analyser la requête utilisateur (B1)
2. Rechercher dans la mémoire (B2) [Pattern recommandé]
3. Consulter ma connaissance de moi-même (B3)
4. Répondre à la requête (B5)

=== RECOMMANDATION ===
Le choix recommandé est 2 (Rechercher dans la mémoire),
basé sur le pattern appris pour ce type de requête.
```

**Choix** : 2 (B2) - Suit le pattern

#### Itération 2 : Recherche → Menu général (pattern)

**Résultat** : Recherche "discuté hier" → Passage automatique au menu général selon pattern

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
...
4. Consulter mes souvenirs (G4) [Pattern recommandé]
...

=== RECOMMANDATION ===
Le choix recommandé est 4 (Consulter mes souvenirs),
basé sur le pattern appris.
```

**Choix** : 4 (G4) - Suit le pattern

#### Itération 3 : Menu souvenirs → Souvenirs récents (pattern)

**Menu proposé** :
```
=== MENU D'ACTIONS INTERNES ===
...
4. Voir les souvenirs récents (S4) [Pattern recommandé]
...

=== RECOMMANDATION ===
Le choix recommandé est 4 (Voir les souvenirs récents),
basé sur le pattern appris.
```

**Choix** : 4 (S4) - Suit le pattern

#### Résultat final

Affichage des souvenirs récents filtrés par date (hier) et triés par MemoryRank.

## Notes importantes

1. **MemoryRank guide la priorisation** : Les éléments avec MemoryRank élevé apparaissent en premier
2. **Recherche sémantique** : Combine similarité + MemoryRank pour meilleure pertinence
3. **Navigation graphe** : Permet d'explorer les connexions entre concepts
4. **Patterns adaptatifs** : S'adaptent au contexte MemoryRank
5. **Menu contextuel** : S'adapte selon la requête et l'historique

## Prochaines étapes

1. **Implémentation** : Voir `PLAN_IMPLEMENTATION_MENU.md`
2. **Architecture** : Voir `ARCHITECTURE_MENU_OPTIMAL.md`


