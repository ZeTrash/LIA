# Guide d'Utilisation - Test de Chat avec GPT-2

## Utilisation

Pour tester de chatter avec le modèle GPT-2 :

```bash
python core/test_chat.py
```

## Commandes Disponibles

- **Tapez votre message** : LIA répondra avec GPT-2
- **`quit` ou `exit`** : Quitter le chat
- **`clear`** : Effacer le contexte (pour repartir à zéro)

## Exemple d'Utilisation

```
============================================================
LIA - Test de Chat avec GPT-2
============================================================

Initialisation du modèle GPT-2...
[OK] Modèle GPT-2 chargé avec succès!

Vous pouvez maintenant chatter avec LIA.
Tapez 'quit' ou 'exit' pour quitter.
Tapez 'clear' pour effacer le contexte.
------------------------------------------------------------

Vous: Bonjour
LIA: [Réponse générée par GPT-2]

Vous: Comment vas-tu ?
LIA: [Réponse générée par GPT-2]

Vous: quit
Au revoir!
```

## Notes

- **Premier chargement** : Le modèle prend quelques secondes à charger la première fois
- **Contexte vide** : Pour l'instant, le contexte mémoire est vide (pas encore de Phase 3)
- **Qualité** : GPT-2 Small est un modèle de base, les réponses peuvent être limitées
- **Performance** : Sur CPU, la génération peut prendre quelques secondes

## Prochaines Étapes

Une fois la Phase 3 (Mémoire) implémentée, le contexte sera automatiquement chargé depuis la base de données, permettant à LIA d'avoir une personnalité et des souvenirs.

