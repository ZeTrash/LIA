# bot_agent

## Présentation

`bot_agent` est un agent conversationnel Python multi-provider (OpenAI GPT, Google Gemini) avec gestion avancée de la mémoire (courte et longue), facilement testable et extensible.

---

## Installation

1. **Cloner le dépôt**
   ```sh
   git clone <url-du-repo>
   cd bot_agent
   ```

2. **Installer les dépendances**
   ```sh
   pip install -r require.txt
   ```
   > Les dépendances principales sont : `openai`, `requests`, `sqlite3` (standard), etc.

---

## Configuration des clés API

1. **Créer un fichier `api_conf.conf`** (non versionné, voir `.gitignore`)

   Exemple de contenu :
   ```ini
   openai_api_key = sk-...votre_cle_openai...
   gemini_1.5_flash_key = AIza...votre_cle_gemini...
   ```

2. **Ne jamais committer ce fichier !**
   - Il contient vos secrets.
   - Il est ignoré par Git.

---

## Utilisation des tests

- **Lancer les tests principaux** :
  ```sh
  python agent_test.py
  ```
  > Le script lit la clé API et le provider dans `api_conf.conf`.
  > Modifiez la variable `provider` dans `agent_test.py` pour choisir entre `openai` et `gemini`.

- **Exemples de scénarios testés** :
  - Envoi de message simple
  - Envoi avec commande (ex : summarize)
  - Test avancé de la mémoire (remplissage, trim, contexte)

---

## Utilisation dans votre code

```python
from agent import Agent

# Exemple d'instanciation
agent = Agent(api_key="...", provider="openai")
response = agent.send_prompt(user_id="user1", message="Bonjour !")
print(response)
```

- Pour Gemini : `provider="gemini"` et utilisez la clé correspondante.
- Le modèle est choisi automatiquement selon le provider, mais peut être forcé.

---

## Sécurité & bonnes pratiques

- **Ne jamais versionner vos clés API** : elles doivent rester dans `api_conf.conf` (local uniquement).
- **Révoquez toute clé exposée** (voir historique GitHub si besoin).
- **Ajoutez vos fichiers sensibles dans `.gitignore`**.
- **Pensez à régénérer la base SQLite (`agent_memory.db`) si besoin** (elle stocke la mémoire longue).

---

## Personnalisation & extension

- **Ajoutez vos propres scénarios de test** dans `TestAgent` ou `TestClient`.
- **Adaptez la gestion mémoire** (taille, trim, etc.) via les paramètres de la classe `Memory`.
- **Ajoutez de nouveaux providers** en étendant la classe `Agent`.

---

## Ressources utiles

- [OpenAI API documentation](https://platform.openai.com/docs/api-reference/introduction)
- [Google Gemini API documentation](https://ai.google.dev/gemini-api/docs/get-started)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) (pour nettoyer l’historique Git)

---

## Support

Pour toute question ou contribution, ouvrez une issue ou une pull request sur le dépôt GitHub.
