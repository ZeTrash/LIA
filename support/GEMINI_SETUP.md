# Configuration Gemini API

## Problème 404 Not Found

Si vous obtenez une erreur 404, voici comment corriger :

### 1. Vérifier la Clé API

La clé API doit être valide et avoir les permissions pour utiliser Gemini API.

### 2. Vérifier le Nom du Modèle

Les modèles disponibles peuvent varier. Essayez :
- `gemini-pro`
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `gemini-1.5-pro-latest`
- `gemini-1.5-flash-latest`

### 3. Vérifier l'URL de l'API

L'URL correcte devrait être :
- `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- ou `https://generativelanguage.googleapis.com/v1/models/{model}:generateContent`

### 4. Tester avec curl

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=VOTRE_CLE" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{
      "parts": [{
        "text": "Hello"
      }]
    }]
  }'
```

### 5. Documentation Officielle

Consultez la documentation officielle de Gemini API :
https://ai.google.dev/api/rest

