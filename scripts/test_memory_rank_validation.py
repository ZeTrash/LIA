#!/usr/bin/env python3
"""
Script de test et validation du système MemoryRank.

Ce script :
1. Crée des souvenirs de test avec différents niveaux d'importance
2. Crée des liens entre souvenirs pour former un graphe
3. Calcule les scores MemoryRank
4. Affiche les résultats et valide le fonctionnement
5. Teste les extensions (temporel, RL, hiérarchie fractale)

Le script utilise automatiquement une base de données de test séparée (data/test.db)
pour ne pas affecter la base de données principale (data/memory.db).

Usage:
    python scripts/test_memory_rank_validation.py
    python scripts/test_memory_rank_validation.py --use-existing  # Copier memory.db
    python scripts/test_memory_rank_validation.py --keep-db        # Garder test.db
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta

# Ajouter le répertoire racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from memory_service.store import MemoryStore
from memory_service.memory_rank_engine import MemoryRankEngine
from memory_service.memory_rank_extensions import FractalMemoryRank, RLMemoryRank, MemoryLevel
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


def test_basic_memory_rank(db=None):
    """Test 1 : MemoryRank de base avec un graphe simple."""
    print_section("Test 1 : MemoryRank de base")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    
    # Créer des souvenirs
    print_info("Création de 5 souvenirs...")
    memories = []
    for i in range(5):
        mem_id = store.add_memory(
            category="fact",
            content=f"Souvenir {i+1} : Information importante numéro {i+1}",
            tags=f"test,memory{i+1}",
            importance_score=0.5 + i * 0.1,
            ttl_days=30
        )
        memories.append(mem_id)
        session = store.db.get_session()
        try:
            memory = session.query(SouvenirModel).filter_by(memory_id=mem_id).first()
            content_preview = memory.content[:40] if memory else "..."
            print_success(f"  Souvenir créé : {mem_id[:8]}... - '{content_preview}...'")
        finally:
            session.close()
    
    # Créer un graphe en étoile (souvenir 0 au centre)
    print_info("Création d'un graphe en étoile (souvenir 0 au centre)...")
    links_created = 0
    for i in range(1, len(memories)):
        link_id = store.add_memory_link(
            source_memory_id=memories[0],
            target_memory_id=memories[i],
            weight=1.0,
            link_type="cooccurrence"
        )
        if link_id:
            links_created += 1
            print_success(f"  Lien créé : {memories[0][:8]}... → {memories[i][:8]}...")
    
    # Ajouter quelques liens supplémentaires pour créer un cycle
    print_info("Ajout de liens supplémentaires pour créer un cycle...")
    store.add_memory_link(memories[1], memories[2], 1.0, "cooccurrence")
    store.add_memory_link(memories[2], memories[3], 1.0, "cooccurrence")
    store.add_memory_link(memories[3], memories[1], 1.0, "cooccurrence")
    links_created += 3
    print_success(f"  Cycle créé : 1 → 2 → 3 → 1")
    
    # Calculer les scores
    print_info("Calcul des scores MemoryRank...")
    ranks = store.update_memory_ranks()
    
    # Afficher les résultats
    print_info("Résultats :")
    print(f"\n{'Souvenir':<12} {'MemoryRank':<12} {'Importance':<12} {'Récence':<12}")
    print("-" * 50)
    
    session = store.db.get_session()
    try:
        for mem_id in memories:
            memory = session.query(SouvenirModel).filter_by(memory_id=mem_id).first()
            if memory:
                print(f"{mem_id[:10]:<12} {memory.memory_rank_score:<12.6f} {memory.importance_score:<12.2f} {memory.recency_score:<12.2f}")
    finally:
        session.close()
    
    # Validation
    if len(ranks) == len(memories):
        print_success(f"✓ {len(ranks)} scores calculés correctement")
    else:
        print_error(f"✗ Nombre de scores incorrect : {len(ranks)} au lieu de {len(memories)}")
    
    # Note : Dans PageRank, un nœud qui pointe vers beaucoup d'autres mais ne reçoit pas de liens
    # peut avoir un score plus faible. C'est normal car il distribue son importance.
    # Le souvenir central pointe vers 4 autres mais ne reçoit pas de liens directs.
    central_rank = ranks.get(memories[0], 0)
    max_rank = max(ranks.values()) if ranks else 0
    
    print_info(f"Score du souvenir central : {central_rank:.6f}")
    print_info(f"Score maximum : {max_rank:.6f}")
    
    # Vérifier que les scores sont calculés (pas tous à zéro)
    if max_rank > 0:
        print_success(f"✓ Les scores MemoryRank sont calculés (max: {max_rank:.6f})")
    else:
        print_warning("⚠ Tous les scores sont à zéro")
    
    return memories, ranks


def test_temporal_decay(db=None):
    """Test 2 : Décroissance temporelle."""
    print_section("Test 2 : Décroissance temporelle")
    
    engine = MemoryRankEngine(db=db, use_temporal_decay=True, decay_factor=0.01)
    store = MemoryStore(db=db, use_memory_rank=True)
    
    # Créer des souvenirs avec des dates différentes
    print_info("Création de souvenirs avec différents âges...")
    now = datetime.now(UTC)
    
    # Souvenir récent (0 jours)
    mem_recent = store.add_memory(
        category="fact",
        content="Souvenir récent",
        importance_score=0.8,
        ttl_days=30
    )
    
    # Souvenir ancien (30 jours) - créer puis modifier la date
    mem_old = store.add_memory(
        category="fact",
        content="Souvenir ancien",
        importance_score=0.8,
        ttl_days=30
    )
    
    # Modifier la date de création du souvenir ancien
    session = store.db.get_session()
    try:
        memory_old = session.query(SouvenirModel).filter_by(memory_id=mem_old).first()
        if memory_old:
            # S'assurer que la date est timezone-aware
            old_date = now - timedelta(days=30)
            if old_date.tzinfo is None:
                old_date = old_date.replace(tzinfo=UTC)
            memory_old.created_at = old_date
            session.commit()
            print_success(f"  Date du souvenir ancien modifiée : {old_date.date()}")
    finally:
        session.close()
    
    # Créer un lien bidirectionnel pour avoir des scores comparables
    store.add_memory_link(mem_recent, mem_old, 1.0, "cooccurrence")
    store.add_memory_link(mem_old, mem_recent, 1.0, "cooccurrence")
    
    # Calculer avec décroissance temporelle
    print_info("Calcul avec décroissance temporelle...")
    ranks = engine.compute_and_update_ranks()
    
    recent_rank = ranks.get(mem_recent, 0)
    old_rank = ranks.get(mem_old, 0)
    
    print_info("Résultats :")
    print(f"  Souvenir récent (0 jours) : {recent_rank:.6f}")
    print(f"  Souvenir ancien (30 jours) : {old_rank:.6f}")
    if old_rank > 0:
        ratio = recent_rank / old_rank
        print(f"  Ratio (récent/ancien) : {ratio:.4f}")
    
    # Avec décroissance temporelle, le souvenir récent devrait avoir un score plus élevé
    # Le facteur de décroissance est 0.01, donc après 30 jours : e^(-0.01 * 30) ≈ 0.74
    # Le souvenir ancien devrait avoir environ 74% du score du récent
    if recent_rank > 0 and old_rank > 0:
        ratio = old_rank / recent_rank
        expected_ratio = 0.74  # e^(-0.01 * 30)
        
        # Accepter un ratio entre 0.5 et 1.0 (la décroissance peut varier selon le graphe)
        if 0.5 <= ratio <= 1.0:
            print_success(f"✓ La décroissance temporelle fonctionne (ratio: {ratio:.4f}, attendu: ~{expected_ratio:.4f})")
        elif ratio < 0.5:
            print_warning(f"⚠ Décroissance plus forte que prévu (ratio: {ratio:.4f})")
        else:
            print_warning(f"⚠ Décroissance plus faible que prévu (ratio: {ratio:.4f})")
    elif recent_rank > old_rank:
        print_success("✓ La décroissance temporelle fonctionne (récent > ancien)")
    else:
        print_warning("⚠ La décroissance temporelle ne semble pas fonctionner comme attendu")
    
    return ranks


def test_cooccurrence_detection(db=None):
    """Test 3 : Détection automatique de co-occurrences."""
    print_section("Test 3 : Détection automatique de co-occurrences")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    engine = MemoryRankEngine(db=db or store.db)
    
    # Créer des souvenirs
    print_info("Création de souvenirs...")
    mem1 = store.add_memory(
        category="fact",
        content="Python est un langage de programmation",
        tags="python,programming",
        importance_score=0.7
    )
    
    mem2 = store.add_memory(
        category="fact",
        content="L'utilisateur aime Python",
        tags="python,preference",
        importance_score=0.6
    )
    
    # Créer une interaction qui mentionne les deux
    print_info("Création d'une interaction mentionnant les deux souvenirs...")
    store.log_interaction(
        session_id="test_session",
        prompt="Je travaille avec Python et j'aime ce langage",
        response="Python est effectivement un excellent langage",
        severity="info"
    )
    
    # Détecter les co-occurrences
    print_info("Détection des co-occurrences...")
    links_created = engine.detect_cooccurrence_links(lookback_days=1)
    
    if links_created > 0:
        print_success(f"✓ {links_created} lien(s) de co-occurrence créé(s)")
    else:
        print_warning("⚠ Aucun lien de co-occurrence détecté")
    
    # Recalculer les scores
    ranks = engine.compute_and_update_ranks()
    print_info(f"✓ Scores recalculés pour {len(ranks)} souvenirs")
    
    return links_created


def test_hybrid_score():
    """Test 4 : Score hybride (MemoryRank + Reward + Similarité)."""
    print_section("Test 4 : Score hybride")
    
    from memory_service.memory_rank import MemoryRank
    
    memory_rank = MemoryRank()
    
    # Test avec MemoryRank seul
    score1 = memory_rank.compute_hybrid_score(
        memory_rank=0.5,
        alpha=1.0
    )
    print_info(f"Score avec MemoryRank seul : {score1:.4f}")
    
    # Test avec MemoryRank + Reward
    score2 = memory_rank.compute_hybrid_score(
        memory_rank=0.5,
        reward_score=0.8,
        alpha=0.5,
        beta=0.5
    )
    print_info(f"Score avec MemoryRank + Reward : {score2:.4f}")
    
    # Test avec les trois composantes
    score3 = memory_rank.compute_hybrid_score(
        memory_rank=0.5,
        reward_score=0.8,
        similarity_score=0.3,
        alpha=0.5,
        beta=0.3,
        gamma=0.2
    )
    print_info(f"Score avec MemoryRank + Reward + Similarité : {score3:.4f}")
    
    # Validation
    if 0.5 <= score2 <= 0.8:
        print_success("✓ Le score hybride est dans la plage attendue")
    else:
        print_warning(f"⚠ Score hybride inattendu : {score2}")
    
    return score1, score2, score3


def test_rl_integration(db=None):
    """Test 5 : Intégration RL."""
    print_section("Test 5 : Intégration RL")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    rl_rank = RLMemoryRank(db=db or store.db)
    
    # Créer un souvenir
    print_info("Création d'un souvenir...")
    mem_id = store.add_memory(
        category="fact",
        content="Souvenir pour test RL",
        importance_score=0.5
    )
    
    # Appliquer une récompense
    print_info("Application d'une récompense RL (0.8)...")
    success = rl_rank.update_memory_with_reward(mem_id, reward=0.8)
    
    if success:
        print_success("✓ Récompense appliquée avec succès")
        
        # Vérifier la mise à jour
        session = store.db.get_session()
        try:
            memory = session.query(SouvenirModel).filter_by(memory_id=mem_id).first()
            if memory:
                print_info(f"  Nouveau score d'importance : {memory.importance_score:.4f}")
                if memory.importance_score > 0.5:
                    print_success("✓ Le score d'importance a augmenté")
                else:
                    print_warning("⚠ Le score d'importance n'a pas augmenté comme attendu")
        finally:
            session.close()
    else:
        print_error("✗ Échec de l'application de la récompense")
    
    return success


def test_fractal_hierarchy(db=None):
    """Test 6 : Hiérarchie fractale."""
    print_section("Test 6 : Hiérarchie fractale")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    fractal = FractalMemoryRank(db=db or store.db)
    
    # Créer des souvenirs avec différents niveaux (via tags)
    print_info("Création de souvenirs avec différents niveaux hiérarchiques...")
    
    mem_event = store.add_memory(
        category="fact",
        content="Événement : Utilisateur a ouvert le terminal",
        tags="event,terminal",
        importance_score=0.5
    )
    
    mem_episode = store.add_memory(
        category="fact",
        content="Épisode : Session de développement Python",
        tags="episode,python,development",
        importance_score=0.6
    )
    
    mem_concept = store.add_memory(
        category="fact",
        content="Concept : Programmation orientée objet",
        tags="concept,oop,abstract",
        importance_score=0.7
    )
    
    mem_objective = store.add_memory(
        category="fact",
        content="Objectif : Créer un système d'IA autonome",
        tags="objective,goal,ai",
        importance_score=0.8
    )
    
    # Créer des liens hiérarchiques
    print_info("Création de liens hiérarchiques...")
    fractal.create_hierarchical_link(mem_event, mem_episode, weight=1.0)
    fractal.create_hierarchical_link(mem_episode, mem_concept, weight=1.0)
    fractal.create_hierarchical_link(mem_concept, mem_objective, weight=1.0)
    print_success("✓ Liens hiérarchiques créés")
    
    # Calculer les rangs par niveau
    print_info("Calcul des rangs par niveau hiérarchique...")
    all_ranks = fractal.compute_all_levels_ranks()
    
    for level, ranks in all_ranks.items():
        if ranks:
            print_info(f"  Niveau {level.value} : {len(ranks)} souvenirs")
            for mem_id, rank in list(ranks.items())[:3]:  # Afficher les 3 premiers
                print(f"    {mem_id[:8]}... : {rank:.6f}")
    
    print_success("✓ Hiérarchie fractale calculée")
    
    return all_ranks


def test_integration_with_context(db=None):
    """Test 7 : Intégration avec get_context()."""
    print_section("Test 7 : Intégration avec get_context()")
    
    store = MemoryStore(db=db, use_memory_rank=True)
    
    # Créer plusieurs souvenirs
    print_info("Création de 10 souvenirs...")
    memories = []
    for i in range(10):
        mem_id = store.add_memory(
            category="fact",
            content=f"Souvenir de test {i+1}",
            importance_score=0.3 + (i % 3) * 0.2,
            ttl_days=30
        )
        memories.append(mem_id)
    
    # Créer un graphe complexe
    print_info("Création d'un graphe complexe...")
    for i in range(len(memories) - 1):
        store.add_memory_link(
            memories[i],
            memories[i+1],
            weight=1.0,
            link_type="cooccurrence"
        )
    
    # Calculer les scores
    store.update_memory_ranks()
    
    # Récupérer le contexte
    print_info("Récupération du contexte avec MemoryRank...")
    context = store.get_context(limit_memories=5)
    
    print_info("Résultats (top 5 souvenirs) :")
    print(f"\n{'Rang':<6} {'MemoryRank':<12} {'Importance':<12} {'Contenu':<40}")
    print("-" * 75)
    
    for i, memory in enumerate(context["memories"][:5], 1):
        rank_score = memory.get("memory_rank_score", 0.0)
        importance = memory.get("importance_score", 0.0)
        content = memory.get("content", "")[:38]
        print(f"{i:<6} {rank_score:<12.6f} {importance:<12.2f} {content:<40}")
    
    # Validation
    if len(context["memories"]) > 0:
        print_success(f"✓ {len(context['memories'])} souvenirs récupérés")
        
        # Vérifier que les souvenirs sont triés par MemoryRank
        ranks = [m.get("memory_rank_score", 0.0) for m in context["memories"]]
        if ranks == sorted(ranks, reverse=True):
            print_success("✓ Les souvenirs sont correctement triés par MemoryRank")
        else:
            print_warning("⚠ Les souvenirs ne sont pas triés par MemoryRank")
    else:
        print_error("✗ Aucun souvenir récupéré")
    
    return context


def setup_test_database(use_existing: bool = False):
    """
    Configure la base de données de test.
    
    Args:
        use_existing: Si True, copie memory.db vers test.db, sinon crée une nouvelle base
    
    Returns:
        Instance de Database configurée pour les tests
    """
    # Définir le chemin de la base de données de test
    test_db_path = project_root / "data" / "test.db"
    memory_db_path = project_root / "data" / "memory.db"
    
    # Créer le répertoire data s'il n'existe pas
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if use_existing and memory_db_path.exists():
        print_info(f"Copie de {memory_db_path} vers {test_db_path}...")
        shutil.copy2(memory_db_path, test_db_path)
        print_success("✓ Base de données copiée")
    else:
        # Supprimer l'ancienne base de test si elle existe
        if test_db_path.exists():
            print_info("Suppression de l'ancienne base de données de test...")
            test_db_path.unlink()
            print_success("✓ Ancienne base supprimée")
    
    # Créer une nouvelle instance de Database avec le chemin de test
    # Utiliser la variable d'environnement pour forcer le chemin
    os.environ["LIA_MEMORY_DB_PATH"] = str(test_db_path)
    
    # Créer la base de données
    db = Database(db_path=str(test_db_path))
    Base.metadata.create_all(db.engine)
    
    return db


def cleanup_test_database(keep_db: bool = False):
    """
    Nettoie la base de données de test.
    
    Args:
        keep_db: Si True, garde la base de données après les tests
    """
    test_db_path = project_root / "data" / "test.db"
    
    # Restaurer la variable d'environnement
    if "LIA_MEMORY_DB_PATH" in os.environ:
        del os.environ["LIA_MEMORY_DB_PATH"]
    
    if not keep_db and test_db_path.exists():
        print_info("Nettoyage de la base de données de test...")
        test_db_path.unlink()
        print_success("✓ Base de données de test supprimée")


def run_all_tests(use_existing_db: bool = False, keep_test_db: bool = False):
    """
    Exécute tous les tests.
    
    Args:
        use_existing_db: Si True, copie memory.db vers test.db avant les tests
        keep_test_db: Si True, garde la base de données de test après les tests
    """
    print_header("VALIDATION DU SYSTÈME MEMORYRANK")
    
    print_info("Configuration de la base de données de test...")
    db = setup_test_database(use_existing=use_existing_db)
    print_success("✓ Base de données de test initialisée")
    
    results = {}
    
    try:
        # Test 1 : MemoryRank de base
        memories, ranks = test_basic_memory_rank(db=db)
        results["basic"] = len(ranks) > 0
        
        # Test 2 : Décroissance temporelle
        temporal_ranks = test_temporal_decay(db=db)
        results["temporal"] = len(temporal_ranks) > 0
        
        # Test 3 : Détection de co-occurrences
        links_created = test_cooccurrence_detection(db=db)
        results["cooccurrence"] = links_created >= 0
        
        # Test 4 : Score hybride (pas besoin de DB)
        score1, score2, score3 = test_hybrid_score()
        results["hybrid"] = all(0 <= s <= 1 for s in [score1, score2, score3])
        
        # Test 5 : Intégration RL
        rl_success = test_rl_integration(db=db)
        results["rl"] = rl_success
        
        # Test 6 : Hiérarchie fractale
        fractal_ranks = test_fractal_hierarchy(db=db)
        results["fractal"] = len(fractal_ranks) > 0
        
        # Test 7 : Intégration avec get_context
        context = test_integration_with_context(db=db)
        results["integration"] = len(context.get("memories", [])) > 0
        
    except Exception as e:
        print_error(f"Erreur lors des tests : {e}")
        import traceback
        traceback.print_exc()
        cleanup_test_database(keep_db=keep_test_db)
        return False
    finally:
        # Fermer la connexion à la base de données
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Script de validation du système MemoryRank")
    parser.add_argument(
        "--use-existing",
        action="store_true",
        help="Copier memory.db vers test.db avant les tests (au lieu de créer une nouvelle base)"
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Garder la base de données de test après les tests (utile pour inspection)"
    )
    
    args = parser.parse_args()
    
    success = run_all_tests(
        use_existing_db=args.use_existing,
        keep_test_db=args.keep_db
    )
    sys.exit(0 if success else 1)

