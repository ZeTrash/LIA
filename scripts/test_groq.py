"""Script de test pour Groq API.

Teste la connexion et les appels à Groq pour diagnostiquer les problèmes.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from support.config import SupportConfig
from support.groq_adapter import GroqAdapter
import httpx
import json


async def test_groq_basic():
    """Test basique de connexion à Groq."""
    print("=" * 70)
    print("Test Groq API - Connexion basique")
    print("=" * 70)
    print()
    
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    if not config.groq_api_key:
        print("❌ Clé API Groq non trouvée dans config/api.conf")
        return False
    
    print(f"✅ Clé API trouvée: {config.groq_api_key[:20]}...")
    print(f"✅ Modèle configuré: {config.groq_model}")
    print()
    
    # Test direct avec httpx
    print("🔍 Test 1: Appel direct à l'API Groq...")
    try:
        headers = {
            "Authorization": f"Bearer {config.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.groq_model,
            "messages": [
                {
                    "role": "user",
                    "content": "Dis simplement 'Bonjour' en une seule ligne."
                }
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = "https://api.groq.com/openai/v1/chat/completions"
            print(f"   URL: {url}")
            print(f"   Modèle: {payload['model']}")
            print(f"   Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            print()
            
            response = await client.post(url, headers=headers, json=payload)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    answer = data["choices"][0]["message"]["content"]
                    print(f"✅ Réponse reçue: {answer}")
                    return True
                else:
                    print(f"⚠️  Réponse invalide: {json.dumps(data, indent=2)}")
                    return False
            else:
                print(f"❌ Erreur HTTP {response.status_code}")
                print(f"   Réponse: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_groq_adapter():
    """Test avec GroqAdapter."""
    print()
    print("=" * 70)
    print("Test Groq API - Via GroqAdapter")
    print("=" * 70)
    print()
    
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    if not config.groq_api_key:
        print("❌ Clé API Groq non trouvée")
        return False
    
    adapter = GroqAdapter(config)
    
    if not adapter.is_available():
        print("❌ GroqAdapter non disponible")
        return False
    
    print(f"✅ GroqAdapter initialisé")
    print(f"   Modèle: {adapter.model}")
    print()
    
    try:
        print("🔍 Test 2: Appel via GroqAdapter.query()...")
        question = "Dis simplement 'Bonjour' en une seule ligne."
        print(f"   Question: {question}")
        print()
        
        answer = await adapter.query(question)
        print(f"✅ Réponse: {answer}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_groq_patterns():
    """Test avec un prompt similaire aux patterns."""
    print()
    print("=" * 70)
    print("Test Groq API - Prompt patterns")
    print("=" * 70)
    print()
    
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    adapter = GroqAdapter(config)
    
    if not adapter.is_available():
        print("❌ GroqAdapter non disponible")
        return False
    
    try:
        print("🔍 Test 3: Prompt de classification de thème...")
        prompt = """Tu es un assistant de classification de requêtes.
Requête de l'utilisateur : "Bonjour"

Thèmes disponibles : "no_pattern", "salutation", "mémoire", "identité", "question", "autre"

Choisis UN SEUL thème auquel pourrait appartenir cette requête.
Réponds UNIQUEMENT avec le nom du thème, sans autre texte."""
        
        print(f"   Prompt (tronqué): {prompt[:100]}...")
        print()
        
        answer = await adapter.query(prompt)
        print(f"✅ Réponse: {answer}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_groq_pattern_format():
    """Test avec le format de réponse patterns."""
    print()
    print("=" * 70)
    print("Test Groq API - Format patterns V2")
    print("=" * 70)
    print()
    
    config = SupportConfig()
    config.load_from_file("config/api.conf")
    
    adapter = GroqAdapter(config)
    
    if not adapter.is_available():
        print("❌ GroqAdapter non disponible")
        return False
    
    try:
        print("🔍 Test 4: Prompt d'apprentissage patterns (format V2)...")
        prompt = """Tu es un assistant d'analyse de stratégies internes.
Tu analyses des suites d'actions internes (menus) choisies par un agent cognitif (LIA) pour traiter une requête utilisateur.

CONTRAINTE IMPORTANTE :
- Ta sortie doit être UNIQUEMENT une suite de codes sous la forme : {Xy, Xy, Xy, ...}
- X est une lettre (B ou G), y est un entier (1, 2, 3, ...).
- N'ajoute AUCUN autre texte avant ou après cette suite.

Contraintes de menus et de transitions (IMPORTANT) :
- Tu démarres TOUJOURS dans le menu de base.
- Dans le menu de base, tu ne peux utiliser que les codes B1, B2, B3.
- Si tu choisis B2, tu passes au menu général.
- Dans le menu général, tu ne peux utiliser que les codes G1, G2, G3, G4, G5, G6.

Contexte :
- Requête de l'utilisateur : "Bonjour"

- Liste d'actions possibles (codes → description) :
  - B1 : Voir la demande de l'utilisateur.
  - B2 : Consulter ma mémoire et me connaitre (menu général).
  - B3 : Répondre à la requête de l'utilisateur.
  - G1 : Connaitre mon identité (qui je suis globalement).
  - G2 : Consulter UNIQUEMENT mes traits (caractéristiques internes : personnalité, façons d'être, styles).
  - G3 : Consulter UNIQUEMENT mon environnement et mes capacités (ce que je peux ou ne peux pas faire).
  - G4 : Consulter mes souvenirs et faits mémorisés (événements passés, informations externes, détails contextuels).
  - G5 : Répondre à la requête de l'utilisateur.
  - G6 : Revenir au menu précédent.

Ta tâche :
1. Proposer une suite de choix internes OPTIMALE pour traiter cette requête utilisateur.
2. Utiliser UNIQUEMENT des codes présents dans la liste d'actions ci-dessus.
3. Ne pas inventer de nouveaux codes ou de nouvelles actions.

En plus : Pour cette requête "Bonjour", voici les thèmes disponibles dans la base : "no_pattern", "salutation", "mémoire", "identité", "question", "autre".
Vous DEVEZ choisir UN thème parmi cette liste pour classer la requête.
Si aucun thème existant ne convient, invente un NOUVEAU nom de thème (ex: greeting, aide, rappel) — mais préfère TOUJOURS un thème existant si possible.

Format de réponse EXIGÉ : {{nom_du_thème},{B2, G4, G5}}
Exemples valides : {{salutation},{B3}} ou {{mémoire},{B2, G4, G5}}
- Sans introduction, sans explication, sans texte additionnel.

Réponds maintenant avec UNIQUEMENT la réponse au format demandé."""
        
        print(f"   Prompt (tronqué): {prompt[:200]}...")
        print()
        
        answer = await adapter.query(prompt)
        print(f"✅ Réponse: {answer}")
        print()
        print("Vérification du format...")
        if answer.strip().startswith("{{") and "}}" in answer:
            print("✅ Format semble correct (commence par {{)")
        else:
            print("⚠️  Format peut être incorrect")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Lance tous les tests."""
    results = []
    
    results.append(await test_groq_basic())
    results.append(await test_groq_adapter())
    results.append(await test_groq_patterns())
    results.append(await test_groq_pattern_format())
    
    print()
    print("=" * 70)
    print("Résumé des tests")
    print("=" * 70)
    print(f"Tests réussis: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ Tous les tests sont passés !")
    else:
        print("⚠️  Certains tests ont échoué")


if __name__ == "__main__":
    asyncio.run(main())

