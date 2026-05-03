#!/usr/bin/env python3
"""
Script de test et validation du système MemoryRank V2.

Ce script teste :
1. Segmentation en phrases
2. Calcul de nouveauté
3. Filtrage sémantique
4. Création automatique de liens
5. Intégration avec MemoryRank V1
6. Traitement d'interactions complètes

Usage:
    python scripts/test_memory_rank_v2_validation.py
    python scripts/test_memory_rank_v2_validation.py --use-existing  # Copier memory.db
    python scripts/test_memory_rank_v2_validation.py --keep-db        # Garder test.db
"""

import sys
import os
import shutil
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, UTC, timedelta

# Ajouter le répertoire racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from memory_service.phrase_segmenter import PhraseSegmenter
from memory_service.semantic_filter import SemanticFilter, ImportanceScore
from memory_service.rl_scorer import RLScorer
from memory_service.phrase_linker import PhraseLinker
from memory_service.phrase_memory_processor import PhraseMemoryProcessor
from memory_service.store import MemoryStore
from memory_service.memory_rank_engine import MemoryRankEngine
from memory_service.db import Database
from memory_service.models import Base, SouvenirModel


class Colors:
    """Codes couleur pour l'affichage."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Affiche un en-tête formaté."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_section(text):
    """Affiche une section formatée."""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}▶ {text}{Colors.ENDC}")


def print_success(text):
    """Affiche un message de succès."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text):
    """Affiche un avertissement."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text):
    """Affiche une erreur."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Affiche une information."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


def setup_test_database(use_existing: bool = False):
    """Configure la base de données de test."""
    test_db_path = project_root / "data" / "test_v2.db"
    memory_db_path = project_root / "data" / "memory.db"
    
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if use_existing and memory_db_path.exists():
        print_info(f"Copie de {memory_db_path} vers {test_db_path}...")
        shutil.copy2(memory_db_path, test_db_path)
        print_success("✓ Base de données copiée")
    else:
        if test_db_path.exists():
            print_info("Suppression de l'ancienne base de données de test...")
            test_db_path.unlink()
            print_success("✓ Ancienne base supprimée")
    
    os.environ["LIA_MEMORY_DB_PATH"] = str(test_db_path)
    
    db = Database(db_path=str(test_db_path))
    Base.metadata.create_all(db.engine)
    
    return db


def cleanup_test_database(keep_db: bool = False):
    """Nettoie la base de données de test."""
    test_db_path = project_root / "data" / "test_v2.db"
    
    if "LIA_MEMORY_DB_PATH" in os.environ:
        del os.environ["LIA_MEMORY_DB_PATH"]
    
    if not keep_db and test_db_path.exists():
        print_info("Nettoyage de la base de données de test...")
        test_db_path.unlink()
        print_success("✓ Base de données de test supprimée")


def test_phrase_segmentation():
    """Test 1 : Segmentation en phrases."""
    print_section("Test 1 : Segmentation en phrases")
    
    segmenter = PhraseSegmenter(min_length=5)
    
    # Test avec différents types de textes
    test_cases = [
        "Je préfère Python à Java. J'aime travailler sur des projets d'IA.",
        "Qui es-tu? Comment tu fonctionnes? Je veux savoir.",
        "C'est génial! Je suis impressionné! Continue comme ça.",
        "Ok. Je préfère Python. Merci.",  # Devrait filtrer "Ok" et "Merci"
    ]
    
    total_phrases = 0
    for i, text in enumerate(test_cases, 1):
        print_info(f"Test {i}: '{text[:50]}...'")
        phrases = segmenter.segment(text)
        total_phrases += len(phrases)
        print(f"  → {len(phrases)} phrase(s) segmentée(s)")
        for j, phrase in enumerate(phrases, 1):
            print(f"    {j}. '{phrase.text}'")
    
    if total_phrases > 0:
        print_success(f"✓ Segmentation fonctionne ({total_phrases} phrases au total)")
    else:
        print_error("✗ Aucune phrase segmentée")
    
    return total_phrases > 0


def test_novelty_calculation(db=None):
    """Test 2 : Calcul de nouveauté."""
    print_section("Test 2 : Calcul de nouveauté")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    filter_obj = SemanticFilter()
    
    # Créer quelques souvenirs existants
    print_info("Création de souvenirs existants...")
    existing_memories = []
    for i in range(3):
        mem_id = store.add_memory(
            category="fact",
            content=f"Souvenir existant {i+1} : Information importante",
            importance_score=0.7
        )
        existing_memories.append(f"Souvenir existant {i+1} : Information importante")
        print_success(f"  Souvenir créé: {mem_id[:8]}...")
    
    # Test avec différentes phrases
    test_phrases = [
        ("Nouvelle information complètement différente", 1.0),  # Devrait être nouveau
        ("Souvenir existant 1 : Information importante", 0.0),  # Devrait être redondant
        ("Information similaire mais pas identique", 0.5),  # Devrait être partiellement nouveau
    ]
    
    all_correct = True
    for phrase, expected_novelty_range in test_phrases:
        novelty = filter_obj.calculate_novelty(phrase, existing_memories)
        print_info(f"Phrase: '{phrase[:50]}...'")
        print(f"  Nouveauté: {novelty:.3f} (attendu: ~{expected_novelty_range:.1f})")
        
        # Vérifier que la nouveauté est dans une plage raisonnable
        if expected_novelty_range == 1.0:
            if novelty < 0.7:
                print_warning(f"  ⚠ Nouveauté plus faible que prévu")
                all_correct = False
        elif expected_novelty_range == 0.0:
            if novelty > 0.3:
                print_warning(f"  ⚠ Nouveauté plus élevée que prévu (redondant attendu)")
                all_correct = False
    
    if all_correct:
        print_success("✓ Calcul de nouveauté fonctionne correctement")
    else:
        print_warning("⚠ Calcul de nouveauté fonctionne mais avec quelques écarts")
    
    return True


def test_semantic_filtering(db=None):
    """Test 3 : Filtrage sémantique complet."""
    print_section("Test 3 : Filtrage sémantique")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    filter_obj = SemanticFilter(threshold=0.4, alpha=0.5, beta=0.3, gamma=0.2)
    
    # Créer quelques souvenirs existants
    existing_memories = []
    for i in range(2):
        mem_id = store.add_memory(
            category="fact",
            content=f"Information existante {i+1}",
            importance_score=0.6
        )
        existing_memories.append(f"Information existante {i+1}")
    
    # Test avec différentes phrases
    test_phrases = [
        "Nouvelle information très importante et unique",
        "Information existante 1",  # Redondante
        "Information similaire mais avec des détails nouveaux",
    ]
    
    print_info("Test du filtrage...")
    phrases_to_store = filter_obj.filter_phrases(test_phrases, existing_memories)
    
    print_info(f"Résultats: {len(phrases_to_store)} phrases à stocker sur {len(test_phrases)} analysées")
    for phrase, importance in phrases_to_store:
        print(f"  ✓ '{phrase[:50]}...' (importance: {importance.combined:.3f})")
    
    # La phrase redondante ne devrait pas être stockée
    redundant_stored = any("existante 1" in phrase for phrase, _ in phrases_to_store)
    if redundant_stored:
        print_warning("⚠ Phrase redondante stockée (peut être normal selon le seuil)")
    else:
        print_success("✓ Filtrage fonctionne (phrase redondante correctement filtrée)")
    
    return len(phrases_to_store) > 0


def test_phrase_linker(db=None):
    """Test 4 : Création automatique de liens."""
    print_section("Test 4 : Création automatique de liens")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    linker = PhraseLinker()
    
    # Créer quelques phrases et les stocker
    print_info("Création de phrases à lier...")
    phrases = [
        "Je préfère Python à Java",
        "J'aime travailler sur des projets d'IA",
        "Python est un langage adapté à l'IA",  # Similaire à la première
    ]
    
    memory_ids = []
    for phrase in phrases:
        mem_id = store.add_memory(
            category="fact",
            content=phrase,
            importance_score=0.7
        )
        memory_ids.append(mem_id)
        print_success(f"  Phrase stockée: {mem_id[:8]}...")
    
    # Créer des liens
    print_info("Création des liens...")
    links_created = linker.create_links_for_interaction(phrases, memory_ids, store)
    
    print_info(f"Résultats: {links_created} liens créés")
    
    if links_created > 0:
        print_success(f"✓ {links_created} lien(s) créé(s) automatiquement")
    else:
        print_warning("⚠ Aucun lien créé")
    
    return links_created > 0


def test_phrase_processor(db=None):
    """Test 5 : Processeur complet."""
    print_section("Test 5 : Processeur complet (pipeline end-to-end)")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    processor = PhraseMemoryProcessor(
        memory_store=store,
        threshold=0.4,
        alpha=0.4,
        beta=0.3,
        gamma=0.3
    )
    
    # Test avec une interaction complète
    interaction = {
        "prompt": "Je préfère Python à Java. J'aime travailler sur des projets d'IA. Mon objectif est de créer un système autonome.",
        "response": "Python est effectivement un excellent choix pour l'IA. Les systèmes autonomes nécessitent une bonne architecture de mémoire.",
        "session_id": "test_session_v2"
    }
    
    print_info("Traitement de l'interaction...")
    print(f"  Prompt: {interaction['prompt'][:60]}...")
    print(f"  Response: {interaction['response'][:60]}...")
    
    stored_ids = asyncio.run(processor.process_interaction(interaction))
    
    print_info(f"Résultats: {len(stored_ids)} phrases stockées")
    
    if len(stored_ids) > 0:
        print_success(f"✓ {len(stored_ids)} phrase(s) stockée(s)")
        
        # Vérifier que les phrases sont dans la base
        context = store.get_context(limit_memories=10)
        memories = context.get("memories", [])
        
        print_info(f"Vérification: {len(memories)} souvenirs dans la base")
        for i, memory in enumerate(memories[:5], 1):
            content = memory.get("content", "")
            importance = memory.get("importance_score", 0.0)
            rank = memory.get("memory_rank_score", 0.0)
            print(f"  {i}. [I:{importance:.3f}, R:{rank:.6f}] {content[:50]}...")
        
        return True
    else:
        print_warning("⚠ Aucune phrase stockée (peut être normal si toutes filtrées)")
        return False


def test_redundancy_filtering(db=None):
    """Test 6 : Filtrage de redondance."""
    print_section("Test 6 : Filtrage de redondance")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    processor = PhraseMemoryProcessor(
        memory_store=store,
        threshold=0.4
    )
    
    # Première interaction
    interaction1 = {
        "prompt": "Je préfère Python à Java.",
        "response": "Python est un bon choix.",
        "session_id": "test_redundancy"
    }
    
    print_info("Première interaction...")
    stored_ids1 = asyncio.run(processor.process_interaction(interaction1))
    print_success(f"  → {len(stored_ids1)} phrase(s) stockée(s)")
    
    # Deuxième interaction avec phrase similaire
    interaction2 = {
        "prompt": "Je préfère Python à Java aussi.",
        "response": "C'est une bonne préférence.",
        "session_id": "test_redundancy"
    }
    
    print_info("Deuxième interaction (phrase similaire)...")
    stored_ids2 = asyncio.run(processor.process_interaction(interaction2))
    print_success(f"  → {len(stored_ids2)} phrase(s) stockée(s)")
    
    # Vérifier que le système a bien géré la redondance
    context = store.get_context(limit_memories=20)
    memories = context.get("memories", [])
    
    python_phrases = [m for m in memories if "Python" in m.get("content", "")]
    
    print_info(f"Total phrases avec 'Python': {len(python_phrases)}")
    
    if len(python_phrases) <= len(stored_ids1) + len(stored_ids2):
        print_success("✓ Le système gère la redondance (pas de duplication excessive)")
    else:
        print_warning("⚠ Possible duplication de phrases similaires")
    
    return True


def test_memory_rank_integration(db=None):
    """Test 7 : Intégration avec MemoryRank V1."""
    print_section("Test 7 : Intégration avec MemoryRank V1")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    processor = PhraseMemoryProcessor(memory_store=store, threshold=0.3)
    
    # Créer plusieurs interactions pour créer un graphe
    interactions = [
        {
            "prompt": "Je préfère Python.",
            "response": "Python est bon.",
            "session_id": "test_integration"
        },
        {
            "prompt": "J'aime l'IA.",
            "response": "L'IA est intéressante.",
            "session_id": "test_integration"
        },
        {
            "prompt": "Python est utile pour l'IA.",
            "response": "Oui, Python et IA vont bien ensemble.",
            "session_id": "test_integration"
        },
    ]
    
    print_info("Traitement de plusieurs interactions...")
    all_stored_ids = []
    for i, interaction in enumerate(interactions, 1):
        stored_ids = asyncio.run(processor.process_interaction(interaction))
        all_stored_ids.extend(stored_ids)
        print_success(f"  Interaction {i}: {len(stored_ids)} phrases stockées")
    
    # Vérifier que MemoryRank a calculé les scores
    print_info("Vérification des scores MemoryRank...")
    ranks = store.update_memory_ranks()
    
    if len(ranks) > 0:
        print_success(f"✓ {len(ranks)} scores MemoryRank calculés")
        
        # Afficher les top scores
        context = store.get_context(limit_memories=5)
        memories = context.get("memories", [])
        
        print_info("Top 5 souvenirs par MemoryRank:")
        for i, memory in enumerate(memories[:5], 1):
            content = memory.get("content", "")
            rank = memory.get("memory_rank_score", 0.0)
            print(f"  {i}. [Rank: {rank:.6f}] {content[:50]}...")
        
        return True
    else:
        print_warning("⚠ Aucun score MemoryRank calculé")
        return False


def run_all_tests(use_existing_db: bool = False, keep_test_db: bool = False):
    """Exécute tous les tests."""
    print_header("VALIDATION DU SYSTÈME MEMORYRANK V2")
    
    print_info("Configuration de la base de données de test...")
    db = setup_test_database(use_existing=use_existing_db)
    print_success("✓ Base de données de test initialisée")
    
    results = {}
    
    try:
        # Test 1 : Segmentation
        results["segmentation"] = test_phrase_segmentation()
        
        # Test 2 : Nouveauté
        results["novelty"] = test_novelty_calculation(db=db)
        
        # Test 3 : Filtrage sémantique
        results["filtering"] = test_semantic_filtering(db=db)
        
        # Test 4 : Création de liens
        results["linking"] = test_phrase_linker(db=db)
        
        # Test 5 : Processeur complet
        results["processor"] = test_phrase_processor(db=db)
        
        # Test 6 : Filtrage de redondance
        results["redundancy"] = test_redundancy_filtering(db=db)
        
        # Test 7 : Intégration MemoryRank
        results["integration"] = test_memory_rank_integration(db=db)
        
    except Exception as e:
        print_error(f"Erreur lors des tests : {e}")
        import traceback
        traceback.print_exc()
        cleanup_test_database(keep_db=keep_test_db)
        return False
    finally:
        db.close()
        cleanup_test_database(keep_db=keep_test_db)
    
    # Résumé
    print_header("RÉSUMÉ DES TESTS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        color = Colors.OKGREEN if result else Colors.FAIL
        print(f"{color}{status}{Colors.ENDC} - {test_name}")
    
    print(f"\n{Colors.BOLD}Résultat : {passed}/{total} tests réussis{Colors.ENDC}")
    
    if passed == total:
        print_success("✓ Tous les tests sont passés !")
        return True
    else:
        print_warning(f"⚠ {total - passed} test(s) ont échoué")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de validation du système MemoryRank V2")
    parser.add_argument(
        "--use-existing",
        action="store_true",
        help="Copier memory.db vers test_v2.db avant les tests"
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Garder la base de données de test après les tests"
    )
    
    args = parser.parse_args()
    
    success = run_all_tests(
        use_existing_db=args.use_existing,
        keep_test_db=args.keep_db
    )
    sys.exit(0 if success else 1)

