"""Test complet de LIA utilisant Gemini - Débat et synthèse sur une thématique."""

import asyncio
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Fonction helper pour print avec flush immédiat
def print_flush(*args, **kwargs):
    """Print avec flush immédiat pour affichage en temps réel."""
    print(*args, **kwargs)
    sys.stdout.flush()

from core import LLMAdapter, CoreConfig
from support import LearningService, SupportConfig, GeminiAdapter
from support.quality_scorer import QualityScorer, calculate_semantic_distance
from memory_service import MemoryAdapter


async def lia_debate_with_gemini(
    core_adapter: LLMAdapter,
    learning_service: LearningService,
    topic: str,
    session_id: str,
    interactive: bool = False
) -> Dict[str, Any]:
    """
    LIA mène un débat avec Gemini sur une thématique.
    
    Processus:
    1. LIA génère une thèse sur le sujet
    2. LIA pose des questions à Gemini pour obtenir l'antithèse
    3. Débat entre LIA (thèse) et Gemini (antithèse)
    4. LIA crée une synthèse
    
    Returns:
        Dictionnaire avec thèse, antithèse, débat et synthèse
    """
    result = {
        "topic": topic,
        "thesis": None,
        "antithesis": None,
        "contradiction_score": None,  # Distance sémantique thèse/antithèse
        "debate": [],
        "convergence_scores": [],  # Scores de convergence à chaque tour
        "synthesis": None,
        "synthesis_validation": None  # Validation de la synthèse
    }
    
    # Initialiser le scorer de qualité
    quality_scorer = QualityScorer()
    
    print_flush("=" * 70)
    print_flush(f"🎯 LIA travaille sur la thématique: {topic}")
    print_flush("=" * 70)
    print_flush()
    
    if interactive:
        input("   [Appuyez sur Entrée pour continuer...]")
        print_flush()
    
    # Étape 1: LIA génère sa thèse
    print_flush("📝 Étape 1: LIA développe sa thèse...")
    print_flush()
    
    thesis_prompt = f"""Tu es LIA, une intelligence artificielle qui réfléchit profondément. 
Sur le sujet "{topic}", développe une thèse argumentée et cohérente. 
Sois précis, structuré et convaincant. Ta réponse doit être une position claire et défendable."""
    
    print_flush("   ⏳ Génération en cours...")
    sys.stdout.flush()
    thesis = await core_adapter.generate(thesis_prompt, session_id=session_id)
    result["thesis"] = thesis
    
    print_flush("🤖 LIA (Thèse):")
    print_flush(f"   {thesis}")
    print_flush()
    
    if interactive:
        input("   [Appuyez sur Entrée pour continuer...]")
        print_flush()
    
    # Étape 2: LIA génère des questions pour obtenir l'antithèse de Gemini
    print_flush("=" * 70)
    print_flush("❓ Étape 2: LIA prépare des questions pour Gemini...")
    print_flush("=" * 70)
    print_flush()
    
    questions_prompt = f"""Tu es LIA. Tu as développé cette thèse sur "{topic}":
"{thesis}"

Tu as accès à Gemini, une source de connaissances externes. Tu peux solliciter Gemini toi-même.

Maintenant, tu dois :
1. Préparer exactement 3 questions critiques à poser à Gemini pour obtenir une perspective opposée (antithèse)
2. Indiquer clairement que tu vas solliciter Gemini pour ces questions

IMPORTANT: Réponds avec UNIQUEMENT les 3 questions, une par ligne, numérotées 1., 2., 3.
Chaque question doit être complète et se terminer par un point d'interrogation.
Ne mets aucun autre texte, juste les 3 questions."""
    
    print_flush("   ⏳ Génération des questions en cours...")
    sys.stdout.flush()
    questions_text = await core_adapter.generate(questions_prompt, session_id=session_id)
    
    # Extraire les questions - méthode robuste
    questions = []
    
    # Méthode 1: Chercher les numéros (1., 2., 3., etc.)
    numbered_pattern = re.compile(r'\d+[\.\)]\s*([^\n\d]+)', re.MULTILINE)
    numbered_matches = numbered_pattern.findall(questions_text)
    if numbered_matches:
        questions = [q.strip() for q in numbered_matches if q.strip() and ('?' in q or len(q) > 20)]
    
    # Méthode 2: Si pas de numéros, chercher les lignes avec "?"
    if not questions or len(questions) < 2:
        lines = questions_text.split('\n')
        for line in lines:
            line = line.strip()
            # Ignorer les lignes vides ou trop courtes
            if line and len(line) > 15:
                # Nettoyer la ligne (enlever numéros, tirets, etc. au début)
                cleaned = re.sub(r'^[\d\-\.\)\s]+', '', line)
                if cleaned and ('?' in cleaned or len(cleaned) > 20):
                    questions.append(cleaned)
    
    # Méthode 3: Essayer d'extraire depuis du JSON mal formé
    if not questions or len(questions) < 2:
        # Chercher des patterns comme "question": "..."
        json_question_pattern = re.compile(r'["\']question[^"\']*["\']\s*:\s*["\']([^"\']+)["\']', re.IGNORECASE)
        json_matches = json_question_pattern.findall(questions_text)
        if json_matches:
            questions.extend([q.strip() for q in json_matches if q.strip()])
    
    # Nettoyer et dédupliquer
    questions = list(dict.fromkeys([q.strip() for q in questions if q.strip() and len(q.strip()) > 10]))
    
    # Fallback final: questions génériques si toujours rien
    if not questions or len(questions) < 2:
        questions = [
            f"Quels sont les arguments contre cette position sur {topic} ?",
            f"Quels sont les risques ou limites de cette approche sur {topic} ?",
            f"Quelles sont les perspectives alternatives sur {topic} ?"
        ]
    
    # Limiter à 3 questions maximum
    questions = questions[:3]
    
    print_flush("🤖 LIA a préparé ces questions:")
    for i, q in enumerate(questions, 1):
        print_flush(f"   {i}. {q}")
    print_flush()
    
    if interactive:
        input("   [Appuyez sur Entrée pour continuer...]")
        print_flush()
    
    # Étape 3: LIA pose les questions à Gemini pour obtenir l'antithèse (PARALLÉLISÉ)
    print_flush("=" * 70)
    print_flush("💬 Étape 3: LIA interroge Gemini pour obtenir l'antithèse...")
    print_flush("=" * 70)
    print_flush()
    
    # Paralléliser les questions à Gemini avec scoring de qualité
    async def ask_gemini_question(question: str, question_num: int) -> Dict[str, Any]:
        """Pose une question à Gemini et retourne la réponse avec score de qualité."""
        print_flush(f"🔍 Question {question_num} à Gemini: {question}")
        print_flush("   ⏳ En attente de réponse Gemini...")
        sys.stdout.flush()
        try:
            gemini_answer = await learning_service.gemini.query(question, context=None)
            
            # Scorer la qualité de la réponse
            quality_score = quality_scorer.score_response(
                response=gemini_answer,
                question=question
            )
            
            print_flush(f"🤖 Gemini (Réponse {question_num}):")
            print_flush(f"   {gemini_answer[:300]}...")
            print_flush(f"   📊 Score qualité: {quality_score['total_score']:.2f} (cohérence: {quality_score['coherence']:.2f}, diversité: {quality_score['lexical_diversity']:.2f}, pas de refus: {quality_score['no_refusal']:.2f})")
            if quality_score['issues']:
                print_flush(f"   ⚠️  Problèmes détectés: {', '.join(quality_score['issues'])}")
            print_flush()
            
            return {
                "question": question,
                "answer": gemini_answer,
                "success": True,
                "quality_score": quality_score
            }
        except Exception as e:
            print_flush(f"❌ Erreur lors de l'interrogation de Gemini (question {question_num}): {e}")
            print_flush()
            return {
                "question": question,
                "answer": None,
                "success": False,
                "error": str(e),
                "quality_score": None
            }
    
    # Lancer toutes les questions en parallèle
    tasks = [ask_gemini_question(q, i+1) for i, q in enumerate(questions)]
    gemini_responses = await asyncio.gather(*tasks)
    
    # Filtrer les réponses réussies
    successful_responses = [r for r in gemini_responses if r.get("success", False)]
    
    # Construire l'antithèse - UNIQUEMENT depuis Gemini (pas de double génération)
    if successful_responses:
        # Demander directement à Gemini de formuler l'antithèse
        antithesis_prompt_gemini = f"""Sur le sujet "{topic}", voici la thèse défendue par LIA:
"{thesis}"

Formule une antithèse claire et argumentée qui s'oppose à cette thèse. Sois convaincant et structuré."""
        
        try:
            print_flush("   ⏳ Génération de l'antithèse par Gemini...")
            sys.stdout.flush()
            antithesis = await learning_service.gemini.query(antithesis_prompt_gemini, context=None)
            
            # Scorer la qualité de l'antithèse
            antithesis_quality = quality_scorer.score_response(
                response=antithesis,
                context=f"Thèse: {thesis}"
            )
            
            # Calculer la distance sémantique (contradiction) entre thèse et antithèse
            contradiction_distance = calculate_semantic_distance(thesis, antithesis)
            result["contradiction_score"] = contradiction_distance
            
            result["antithesis"] = antithesis
            print_flush("=" * 70)
            print_flush("🔄 Antithèse (générée par Gemini):")
            print_flush("=" * 70)
            print_flush()
            print_flush(f"   {antithesis}")
            print_flush()
            print_flush(f"📊 Analyse de contradiction:")
            print_flush(f"   Distance sémantique thèse/antithèse: {contradiction_distance:.3f}")
            if contradiction_distance < 0.3:
                print_flush(f"   ⚠️  Distance faible ({contradiction_distance:.3f}) - risque de faux débat")
            elif contradiction_distance > 0.7:
                print_flush(f"   ✅ Distance élevée ({contradiction_distance:.3f}) - opposition claire")
            else:
                print_flush(f"   ✅ Distance modérée ({contradiction_distance:.3f}) - débat valide")
            print_flush(f"   Score qualité antithèse: {antithesis_quality['total_score']:.2f}")
            print_flush()
            
            if interactive:
                input("   [Appuyez sur Entrée pour continuer...]")
                print_flush()
        except Exception as e:
            print(f"⚠️  Erreur lors de la génération de l'antithèse par Gemini: {e}")
            print("   Utilisation d'un fallback depuis les réponses...")
            # Fallback: construire l'antithèse à partir des réponses réussies
            fallback_prompt = f"""À partir de ces réponses de Gemini sur "{topic}":
{chr(10).join([f"Q: {r['question']}\nR: {r['answer']}" for r in successful_responses])}

Synthétise une antithèse cohérente et argumentée qui s'oppose à la thèse initiale."""
            antithesis = await core_adapter.generate(fallback_prompt, session_id=session_id)
            result["antithesis"] = antithesis
            print("=" * 70)
            print("🔄 Antithèse (fallback depuis réponses Gemini):")
            print("=" * 70)
            print()
            print(f"   {antithesis}")
            print()
    else:
        result["antithesis"] = "Impossible d'obtenir l'antithèse de Gemini (toutes les questions ont échoué)."
        print("=" * 70)
        print("❌ Impossible d'obtenir l'antithèse")
        print("=" * 70)
        print()
        print("   Toutes les questions à Gemini ont échoué.")
        print()
    
    # Étape 4: Débat entre LIA (thèse) et Gemini (antithèse) - 3-5 tours avec convergence
    print_flush("=" * 70)
    print_flush("⚔️  Étape 4: Débat entre LIA (thèse) et Gemini (antithèse)...")
    print_flush("=" * 70)
    print_flush()
    
    debate_rounds = 4  # 3-5 tours pour un vrai débat dialectique
    debate_log = []
    convergence_threshold = 0.15  # Seuil de convergence (distance entre positions)
    
    for round_num in range(1, debate_rounds + 1):
        print_flush(f"--- Tour {round_num} du débat ---")
        print_flush()
        
        # LIA défend sa thèse
        if round_num == 1:
            defense_prompt = f"""Tu es LIA. Tu défends ta thèse sur "{topic}":
THÈSE: {thesis}

Face à cette antithèse:
ANTITHÈSE: {result['antithesis']}

Défends ta position avec des arguments solides. Sois convaincant et respectueux."""
        else:
            # Tours suivants: LIA répond aux arguments de Gemini
            last_gemini_arg = debate_log[-1].get("gemini_argument") or ""
            defense_prompt = f"""Tu es LIA. Tu continues à défendre ta thèse sur "{topic}":
THÈSE: {thesis}

Gemini vient de dire: "{last_gemini_arg}"

Réponds à cet argument tout en défendant ta position."""
        
        print_flush("   ⏳ LIA génère son argument...")
        sys.stdout.flush()
        lia_argument = await core_adapter.generate(defense_prompt, session_id=session_id)
        debate_log.append({
            "round": round_num,
            "lia_argument": lia_argument
        })
        
        print_flush(f"🤖 LIA (Défense de la thèse):")
        print_flush(f"   {lia_argument[:300]}...")
        print_flush()
        
        # Gemini répond avec l'antithèse
        gemini_debate_question = f"""Tu défends l'antithèse sur "{topic}". 
Voici l'antithèse: {result['antithesis']}
LIA vient de dire: "{lia_argument}"

Réponds en défendant l'antithèse avec des arguments solides."""
        
        try:
            gemini_argument = await learning_service.gemini.query(gemini_debate_question, context=None)
            
            # Scorer la qualité de la réponse Gemini
            gemini_quality = quality_scorer.score_response(
                response=gemini_argument,
                context=f"Argument LIA: {lia_argument}"
            )
            
            if gemini_argument and gemini_quality['is_valid']:
                debate_log[-1]["gemini_argument"] = gemini_argument
                debate_log[-1]["gemini_quality"] = gemini_quality
                
                print_flush(f"🤖 Gemini (Défense de l'antithèse):")
                print_flush(f"   {gemini_argument[:300]}...")
                print_flush(f"   📊 Score qualité: {gemini_quality['total_score']:.2f}")
                print_flush()
                
                # Calculer convergence (distance entre arguments LIA et Gemini)
                if round_num > 1:
                    # Comparer avec le tour précédent
                    prev_lia = debate_log[-2].get("lia_argument") or ""
                    prev_gemini = debate_log[-2].get("gemini_argument") or ""
                    
                    # Distance entre positions actuelles
                    current_distance = calculate_semantic_distance(lia_argument, gemini_argument)
                    prev_distance = calculate_semantic_distance(prev_lia, prev_gemini) if prev_gemini else 1.0
                    
                    convergence = prev_distance - current_distance  # Convergence si distance diminue
                    result["convergence_scores"].append({
                        "round": round_num,
                        "distance": current_distance,
                        "convergence": convergence
                    })
                    
                    print_flush(f"   📈 Convergence: {convergence:+.3f} (distance: {current_distance:.3f})")
                    if convergence > convergence_threshold:
                        print_flush(f"   ✅ Convergence significative détectée!")
                    print_flush()
                
                if interactive and round_num < debate_rounds:
                    input("   [Appuyez sur Entrée pour le tour suivant...]")
                    print_flush()
            else:
                raise ValueError(f"Réponse Gemini invalide (score: {gemini_quality.get('total_score', 0)})")
        except Exception as e:
            print(f"❌ Erreur lors de la réponse de Gemini: {e}")
            print("⚠️  Le débat ne peut pas continuer sans réponse de Gemini valide.")
            print()
            debate_log[-1]["gemini_argument"] = None
            debate_log[-1]["gemini_error"] = str(e)
            
            # Si Gemini ne répond pas, arrêter le débat
            if round_num < debate_rounds:
                print(f"⚠️  Arrêt du débat au tour {round_num} (Gemini ne répond plus).")
                break
    
    result["debate"] = debate_log
    
    # Étape 5: LIA crée une synthèse
    print_flush("=" * 70)
    print_flush("✨ Étape 5: LIA crée une synthèse...")
    print_flush("=" * 70)
    print_flush()
    
    if interactive:
        input("   [Appuyez sur Entrée pour continuer...]")
        print_flush()
    
    synthesis_prompt = f"""Tu es LIA. Tu as mené un débat sur "{topic}".

THÈSE (ta position initiale):
{thesis}

ANTITHÈSE (position de Gemini):
{result['antithesis']}

DÉBAT:
{chr(10).join([f"Tour {d['round']}: LIA: {d['lia_argument'][:150]}... | Gemini: {(d.get('gemini_argument') or 'N/A')[:150]}..." for d in debate_log])}

Maintenant, crée une synthèse qui trouve un terrain d'entente entre la thèse et l'antithèse. 
La synthèse doit être équilibrée, nuancée et intégrer les meilleurs éléments des deux positions."""
    
    print_flush("   ⏳ Génération de la synthèse en cours...")
    sys.stdout.flush()
    synthesis = await core_adapter.generate(synthesis_prompt, session_id=session_id)
    result["synthesis"] = synthesis
    
    print_flush("🤖 LIA (Synthèse):")
    print_flush(f"   {synthesis}")
    print_flush()
    
    # Validation de la synthèse
    print_flush("=" * 70)
    print_flush("🔍 Validation de la synthèse...")
    print_flush("=" * 70)
    print_flush()
    
    synthesis_validation = {
        "contains_thesis_elements": False,
        "contains_antithesis_elements": False,
        "neutral_tone": False,
        "overall_valid": False
    }
    
    # Vérifier présence d'éléments de la thèse
    thesis_keywords = set(re.findall(r'\b\w{5,}\b', thesis.lower()))
    synthesis_lower = synthesis.lower()
    thesis_found = sum(1 for kw in thesis_keywords if kw in synthesis_lower)
    thesis_coverage = thesis_found / max(len(thesis_keywords), 1)
    synthesis_validation["contains_thesis_elements"] = thesis_coverage > 0.1
    
    # Vérifier présence d'éléments de l'antithèse
    if result["antithesis"]:
        antithesis_keywords = set(re.findall(r'\b\w{5,}\b', result["antithesis"].lower()))
        antithesis_found = sum(1 for kw in antithesis_keywords if kw in synthesis_lower)
        antithesis_coverage = antithesis_found / max(len(antithesis_keywords), 1)
        synthesis_validation["contains_antithesis_elements"] = antithesis_coverage > 0.1
    
    # Vérifier ton neutre (absence de mots polarisés)
    polarized_words = ["absolument", "totalement", "jamais", "toujours", "impossible", "certainement"]
    neutral_score = 1.0 - min(sum(1 for word in polarized_words if word in synthesis_lower) / 5.0, 1.0)
    synthesis_validation["neutral_tone"] = neutral_score > 0.6
    
    # Validation globale
    synthesis_validation["overall_valid"] = (
        synthesis_validation["contains_thesis_elements"] and
        synthesis_validation["contains_antithesis_elements"] and
        synthesis_validation["neutral_tone"]
    )
    
    result["synthesis_validation"] = synthesis_validation
    
    print_flush(f"📊 Résultats de validation:")
    print_flush(f"   ✅ Contient éléments thèse: {synthesis_validation['contains_thesis_elements']} (couverture: {thesis_coverage:.2%})")
    if result["antithesis"]:
        print_flush(f"   ✅ Contient éléments antithèse: {synthesis_validation['contains_antithesis_elements']} (couverture: {antithesis_coverage:.2%})")
    print_flush(f"   ✅ Ton neutre: {synthesis_validation['neutral_tone']} (score: {neutral_score:.2f})")
    print_flush(f"   {'✅' if synthesis_validation['overall_valid'] else '⚠️ '} Synthèse valide: {synthesis_validation['overall_valid']}")
    print_flush()
    
    # Sauvegarder le débat dans la mémoire (chaque tour + synthèse)
    if learning_service.memory:
        try:
            print_flush("💾 Sauvegarde dans la mémoire...")
            sys.stdout.flush()
            # Sauvegarder chaque tour de débat
            for debate_round in debate_log:
                if debate_round.get("gemini_argument"):  # Seulement si Gemini a répondu
                    round_content = f"""Débat sur {topic} - Tour {debate_round['round']}:
LIA: {debate_round['lia_argument']}
Gemini: {debate_round['gemini_argument']}"""
                    
                    learning_service.memory.add_memory_from_interaction(
                        content=round_content,
                        category="debate_round",
                        importance_score=0.8
                    )
            
            # Sauvegarder la synthèse finale
            synthesis_content = f"""Débat sur {topic} - SYNTHÈSE:
THÈSE: {thesis}
ANTITHÈSE: {result['antithesis']}
SYNTHÈSE: {synthesis}"""
            
            learning_service.memory.add_memory_from_interaction(
                content=synthesis_content,
                category="debate_synthesis",
                importance_score=0.9
            )
            print_flush("✅ Débat complet sauvegardé dans la mémoire (tours + synthèse)")
            print_flush()
        except Exception as e:
            print_flush(f"⚠️  Erreur lors de la sauvegarde: {e}")
            print_flush()
    
    return result


async def test_lia_with_gemini(interactive: bool = False):
    """
    Test complet de LIA utilisant Gemini pour débattre et synthétiser.
    
    Args:
        interactive: Si True, pause entre chaque étape pour suivi pas à pas
    """
    print_flush("=" * 70)
    print_flush("LIA - Test de Débat et Synthèse avec Gemini")
    if interactive:
        print_flush("   Mode interactif activé (pause entre étapes)")
    print_flush("=" * 70)
    print_flush()
    
    # 1. Initialisation
    print_flush("🔧 Initialisation de LIA...")
    print_flush()
    
    # Configuration du noyau primaire
    core_config = CoreConfig(
        model_path="models/Qwen/Qwen2.5-1.5B-Instruct",
        quantize=True,
        quantization_bits=4,
        max_length=512,  # Augmenté pour thèse/antithèse/synthèse complètes
        temperature=0.7
    )
    
    # Configuration du noyau d'appui
    support_config = SupportConfig()
    support_config.load_from_file("config/api.conf")
    
    if not support_config.gemini_api_key or support_config.gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("⚠️  Clé API Gemini non configurée dans config/api.conf")
        print("   Le test nécessite Gemini pour fonctionner.")
        return
    
    print_flush(f"✅ Configuration Gemini chargée")
    
    # Initialiser les services
    print_flush("   ⏳ Initialisation des services...")
    sys.stdout.flush()
    memory = MemoryAdapter()
    
    learning_service = LearningService(
        config=support_config,
        memory_adapter=memory
    )
    
    # Passer le gemini_adapter à LLMAdapter pour la conscience environnementale
    # Activer le système de planification cognitive (Phase 2-6)
    core_adapter = LLMAdapter(
        core_config,
        use_memory=True,
        gemini_adapter=learning_service.gemini if hasattr(learning_service, 'gemini') else None,
        use_cognitive_planner=True  # Activer le nouveau système
    )
    
    print_flush("✅ Service d'apprentissage initialisé")
    print_flush("✅ Noyau primaire initialisé avec mémoire et conscience environnementale")
    print_flush()
    
    # 2. Demander à LIA de travailler sur une thématique
    session_id = "test_lia_debate_session"
    
    print_flush("=" * 70)
    print_flush("💬 Demande à LIA de travailler sur une thématique")
    print_flush("=" * 70)
    print_flush()
    
    # Thématique à explorer
    topic = "L'intelligence artificielle va-t-elle remplacer les humains au travail ?"
    
    print_flush(f"👤 Vous: LIA, peux-tu travailler sur cette thématique: {topic}")
    print_flush()
    
    # LIA accepte et commence le travail
    print_flush("   ⏳ LIA réfléchit...")
    sys.stdout.flush()
    acceptance = await core_adapter.generate(
        f"L'utilisateur me demande de travailler sur cette thématique: {topic}. Je dois répondre brièvement que j'accepte et que je vais commencer.",
        session_id=session_id
    )
    print_flush(f"🤖 LIA: {acceptance}")
    print_flush()
    
    if interactive:
        input("   [Appuyez sur Entrée pour commencer le débat...]")
        print_flush()
    
    # 3. LIA mène le débat avec Gemini
    try:
        debate_result = await lia_debate_with_gemini(
            core_adapter=core_adapter,
            learning_service=learning_service,
            topic=topic,
            session_id=session_id,
            interactive=interactive
        )
        
        # 4. Résumé final avec vérifications de cohérence
        print_flush("=" * 70)
        print_flush("📊 Résumé du processus")
        print_flush("=" * 70)
        print_flush()
        
        # Vérifications de cohérence
        checks = {
            "thesis_valid": debate_result['thesis'] and len(debate_result['thesis']) > 50,
            "antithesis_valid": debate_result['antithesis'] and len(debate_result['antithesis']) > 50,
            "debate_rounds_valid": len(debate_result['debate']) > 0,
            "synthesis_valid": debate_result['synthesis'] and len(debate_result['synthesis']) > 50,
            "gemini_responses_valid": all(
                (d.get("gemini_argument") or "") and len(d.get("gemini_argument") or "") > 10 
                for d in debate_result['debate']
            )
        }
        
        print_flush(f"✅ Thème: {debate_result['topic']}")
        print_flush(f"{'✅' if checks['thesis_valid'] else '⚠️ '} Thèse développée: {len(debate_result['thesis'])} caractères")
        print_flush(f"{'✅' if checks['antithesis_valid'] else '⚠️ '} Antithèse obtenue: {len(debate_result['antithesis'])} caractères")
        if debate_result.get('contradiction_score') is not None:
            contradiction = debate_result['contradiction_score']
            print_flush(f"   📊 Contradiction thèse/antithèse: {contradiction:.3f} {'✅' if contradiction > 0.3 else '⚠️ '}")
        print_flush(f"{'✅' if checks['debate_rounds_valid'] else '⚠️ '} Tours de débat: {len(debate_result['debate'])}")
        if debate_result.get('convergence_scores'):
            avg_convergence = sum(c['convergence'] for c in debate_result['convergence_scores']) / len(debate_result['convergence_scores'])
            print_flush(f"   📈 Convergence moyenne: {avg_convergence:+.3f} {'✅' if avg_convergence > 0 else '⚠️ '}")
        print_flush(f"{'✅' if checks['synthesis_valid'] else '⚠️ '} Synthèse créée: {len(debate_result['synthesis'])} caractères")
        if debate_result.get('synthesis_validation'):
            synth_val = debate_result['synthesis_validation']
            print_flush(f"   {'✅' if synth_val['overall_valid'] else '⚠️ '} Synthèse validée: {synth_val['overall_valid']}")
        print_flush(f"{'✅' if checks['gemini_responses_valid'] else '⚠️ '} Réponses Gemini valides: {sum(1 for d in debate_result['debate'] if d.get('gemini_argument'))}/{len(debate_result['debate'])}")
        print_flush()
        
        # Avertissements si problèmes détectés
        if not all(checks.values()):
            print_flush("⚠️  Avertissements:")
            if not checks['thesis_valid']:
                print_flush("   - Thèse trop courte ou invalide")
            if not checks['antithesis_valid']:
                print_flush("   - Antithèse trop courte ou invalide")
            if not checks['debate_rounds_valid']:
                print_flush("   - Aucun tour de débat n'a été effectué")
            if not checks['gemini_responses_valid']:
                print_flush("   - Certaines réponses de Gemini sont manquantes ou invalides")
            print_flush()
        
        # Vérification de la mémoire
        context = memory.get_context()
        print_flush(f"📝 Souvenirs dans la mémoire: {len(context['memories'])}")
        print_flush()
        
        print_flush("=" * 70)
        print_flush("🎉 Test terminé avec succès !")
        print_flush("=" * 70)
        
    except Exception as e:
        print(f"❌ Erreur lors du débat: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test de débat LIA-Gemini")
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Mode interactif: pause entre chaque étape pour suivi pas à pas"
    )
    args = parser.parse_args()
    
    try:
        asyncio.run(test_lia_with_gemini(interactive=args.interactive))
    except KeyboardInterrupt:
        print_flush("\n\n⚠️  Test interrompu par l'utilisateur")
    except Exception as e:
        print_flush(f"\n\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
