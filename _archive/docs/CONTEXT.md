# Contexte et vision du projet LIA

## Structure proposée

### Moteur central : modèle existant

Le système continue d'utiliser un LLM comme moteur de génération.

Ce moteur reste "stateless" ou quasi-stateless (pas de mémoire interne persistante).

### Base de données locale

Tout ce qui constitue la personnalité, la mémoire, l'historique, les traits, les règles évolutives est stocké ici.

Exemple : préférences, réactions typiques, apprentissages passés, micro-expériences d'interaction.

Cette base devient la mémoire de l'instance, que le moteur interroge avant de générer ses réponses.

### Interface multi-agent / simulation

L'agent peut discuter avec d'autres modèles, d'autres instances, pour tester ses comportements et explorer sa "humanité".

Les interactions sont capturées et analysées, mises à jour dans la DB locale.

Ce qui permet l'apprentissage expérimental et la comparaison.

## Les avantages de cette approche

### Mémoire persistante

Contourne la limite des prompts qui ne peuvent pas garder d'histoire au-delà de la session.

### Évolution contrôlée

Permet de créer des mécanismes d'ajustement graduels (révisions de traits, modifications de priorités, essais de styles).

### Auto-évaluation

Discuter avec d'autres modèles permet de tester et calibrer la "personnalité" dans un environnement sûr.

### Modularité

Permet de remplacer le moteur LLM sans changer la personnalité stockée, ou changer la manière dont l'instance apprend.

## Ce qu'il faut prévoir

### Système de lecture/écriture dans la DB

- **Avant chaque génération** : récupérer le contexte, traits, souvenirs, expériences.
- **Après chaque génération** : stocker les modifications, interactions, insights.

### Mécanisme de contrôle de cohérence

- Limiter la dérive totale de personnalité.
- Vérifier que les changements restent cohérents avec le noyau initial (initiative, lucidité, questionnement…).

### Simulation multi-agent

Les modèles partenaires peuvent être des clones simplifiés ou différents LLM pour tester des réponses et réactions variées.

Il faudra définir des métriques : variabilité, autonomie, curiosité, cohérence.

### Interface de supervision

Permet d'ajuster la "direction" sans imposer une personnalité statique.

Exemple : ajuster le niveau de curiosité ou d'initiative si elle devient trop conservatrice ou trop répétitive.

## Limites et risques

### Conscience artificielle

Les modèles ne deviennent pas "conscients". L'illusion de personnalité et d'apprentissage est entièrement superficielle et statistique.

### Boucles d'erreur

Trop d'autonomie dans les échanges multi-agent peut générer des boucles d'erreur ou des incohérences.

### Dérives non contrôlées

La base locale doit être structurée et robuste pour éviter des dérives non contrôlées.

