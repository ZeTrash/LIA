#!/usr/bin/env python3
"""
Exemple d'utilisation du système MemoryRank V2 - Traitement par phrases.

Cet exemple montre comment utiliser le PhraseMemoryProcessor pour traiter
des interactions et stocker automatiquement les phrases importantes.
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from memory_service.phrase_memory_processor import PhraseMemoryProcessor
from memory_service.store import MemoryStore


async def main():
    """Exemple principal."""
    print("=" * 70)
    print("Exemple : MemoryRank V2 - Traitement par phrases")
    print("=" * 70)
    print()
    
    # Créer le processeur
    print("Initialisation du processeur...")
    store = MemoryStore(use_memory_rank=True)
    processor = PhraseMemoryProcessor(
        memory_store=store,
        alpha=0.4,  # Poids nouveauté
        beta=0.3,   # Poids RL
        gamma=0.3,  # Poids centralité
        threshold=0.4  # Seuil de stockage (plus bas pour l'exemple)
    )
    print("✓ Processeur initialisé\n")
    
    # Exemple d'interactions
    interactions = [
        {
            "prompt": "Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
            "response": "Python est effectivement un excellent choix pour l'IA et le machine learning.",
            "session_id": "example_session_1"
        },
        {
            "prompt": "Mon objectif est de créer un système autonome. Je veux qu'il apprenne de ses expériences.",
            "response": "C'est un objectif ambitieux et intéressant. Les systèmes autonomes nécessitent une bonne architecture de mémoire.",
            "session_id": "example_session_1"
        },
        {
            "prompt": "Je préfère Python à Java.",  # Redondant avec la première
            "response": "C'est noté.",
            "session_id": "example_session_2"
        },
    ]
    
    # Traiter chaque interaction
    for i, interaction in enumerate(interactions, 1):
        print(f"\n{'='*70}")
        print(f"Interaction {i}")
        print(f"{'='*70}")
        print(f"Prompt: {interaction['prompt']}")
        print(f"Response: {interaction['response']}")
        print()
        
        # Traiter l'interaction
        stored_ids = await processor.process_interaction(interaction)
        
        print(f"✓ {len(stored_ids)} phrase(s) stockée(s)")
        for idx, mem_id in enumerate(stored_ids, 1):
            print(f"  {idx}. {mem_id[:8]}...")
    
    # Afficher les souvenirs stockés
    print(f"\n{'='*70}")
    print("Souvenirs stockés")
    print(f"{'='*70}")
    
    context = store.get_context(limit_memories=20)
    memories = context.get("memories", [])
    
    print(f"\nTotal: {len(memories)} souvenirs\n")
    
    for i, memory in enumerate(memories[:10], 1):
        content = memory.get("content", "")
        importance = memory.get("importance_score", 0.0)
        rank = memory.get("memory_rank_score", 0.0)
        print(f"{i}. [Importance: {importance:.3f}, Rank: {rank:.6f}]")
        print(f"   {content[:80]}...")
        print()
    
    # Afficher les statistiques
    print(f"\n{'='*70}")
    print("Statistiques")
    print(f"{'='*70}")
    
    total_phrases = sum(len(interaction['prompt'].split('.')) + len(interaction.get('response', '').split('.')) 
                       for interaction in interactions)
    total_stored = len(memories)
    
    print(f"Phrases totales dans les interactions: ~{total_phrases}")
    print(f"Phrases stockées: {total_stored}")
    print(f"Taux de filtrage: {(1 - total_stored/total_phrases)*100:.1f}%" if total_phrases > 0 else "N/A")
    print()
    
    print("✓ Exemple terminé")


if __name__ == "__main__":
    asyncio.run(main())

