"""Calcul des métriques comportementales."""

import re
import math
from typing import Any, Dict, List, Set, Optional
from collections import Counter

from .schemas import MultiAgentMessage, BehavioralMetrics
from .protocol import calculate_content_hash


def extract_topics(content: str) -> Set[str]:
    """
    Extrait les sujets/thèmes d'un message (simplifié).
    
    En production, on pourrait utiliser TF-IDF, embeddings, ou NLP.
    """
    # Extraction basique par mots-clés communs
    keywords = [
        "philosophie", "philosophy", "science", "art", "musique", "music",
        "technologie", "technology", "intelligence", "artificielle", "ai",
        "émotion", "emotion", "créativité", "creativity", "réflexion", "reflection",
        "éthique", "ethics", "morale", "moral", "société", "society"
    ]
    
    content_lower = content.lower()
    found_topics = set()
    
    for keyword in keywords:
        if keyword in content_lower:
            found_topics.add(keyword)
    
    # Si aucun mot-clé trouvé, utiliser les premiers mots significatifs
    if not found_topics:
        words = re.findall(r'\b\w{4,}\b', content_lower)
        found_topics = set(words[:5])  # Prendre les 5 premiers mots significatifs
    
    return found_topics


def is_question(content: str) -> bool:
    """Détecte si un message est une question."""
    return content.strip().endswith("?") or "?" in content


def is_direct_response(message: MultiAgentMessage, previous_message: Optional[MultiAgentMessage]) -> bool:
    """Détecte si un message est une réponse directe au précédent."""
    if not previous_message:
        return False
    
    # Vérifier si le message fait référence au précédent
    content_lower = message.content.lower()
    prev_content_lower = previous_message.content.lower()[:50]  # Premiers 50 caractères
    
    # Mots de réponse courants
    response_indicators = ["oui", "non", "d'accord", "je pense", "je crois", "oui", "no", "yes", "i think"]
    
    return any(indicator in content_lower for indicator in response_indicators)


def calculate_variability(messages: List[MultiAgentMessage]) -> float:
    """
    Calcule la variabilité (diversité des réponses et comportements).
    
    Formule: (entropy_responses / max_entropy) * 0.6 + diversity_topics * 0.4
    """
    if not messages:
        return 0.0
    
    # 1. Calculer l'entropie de Shannon sur les réponses
    content_hashes = [calculate_content_hash(msg.content) for msg in messages]
    hash_counts = Counter(content_hashes)
    total = len(messages)
    
    entropy = 0.0
    max_entropy = math.log2(total) if total > 0 else 1.0
    
    for count in hash_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    
    # 2. Calculer la diversité des sujets
    all_topics = set()
    for msg in messages:
        all_topics.update(extract_topics(msg.content))
    
    # Normalisation approximative : diversité = topics uniques / (total messages / 3)
    diversity = len(all_topics) / max(1, total // 3)
    diversity = min(1.0, diversity)  # Capping à 1.0
    
    # 3. Combinaison pondérée
    variability = normalized_entropy * 0.6 + diversity * 0.4
    return min(1.0, max(0.0, variability))


def calculate_autonomy(messages: List[MultiAgentMessage], agent_id: str) -> float:
    """
    Calcule l'autonomie (capacité à prendre des initiatives).
    
    Formule: (initiated_messages / total_messages) * 0.6 + (questions_count / total_messages) * 0.4
    """
    agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
    total = len(agent_messages)
    
    if total == 0:
        return 0.0
    
    # 1. Compter les messages initiés
    initiated = 0
    for i, msg in enumerate(agent_messages):
        if i == 0:
            initiated += 1
        else:
            prev_msg = agent_messages[i - 1]
            if not is_direct_response(msg, prev_msg):
                initiated += 1
    
    initiated_ratio = initiated / total
    
    # 2. Compter les questions
    questions = sum(1 for msg in agent_messages if is_question(msg.content))
    questions_ratio = questions / total
    
    # 3. Combinaison pondérée
    autonomy = initiated_ratio * 0.6 + questions_ratio * 0.4
    return min(1.0, max(0.0, autonomy))


def calculate_curiosity(messages: List[MultiAgentMessage], agent_id: str) -> float:
    """
    Calcule la curiosité (propension à explorer et questionner).
    
    Formule: (questions_count / total_messages) * 0.5 + (new_topics / max(1, total_topics)) * 0.5
    """
    agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
    total = len(agent_messages)
    
    if total == 0:
        return 0.0
    
    # 1. Compter les questions
    questions = sum(1 for msg in agent_messages if is_question(msg.content))
    questions_ratio = questions / total
    
    # 2. Calculer l'exploration de nouveaux sujets
    all_topics = set()
    new_topics_count = 0
    
    for msg in agent_messages:
        msg_topics = extract_topics(msg.content)
        new_topics = msg_topics - all_topics
        if new_topics:
            new_topics_count += len(new_topics)
        all_topics.update(msg_topics)
    
    total_topics = len(all_topics)
    exploration_ratio = new_topics_count / max(1, total_topics)
    
    # 3. Combinaison pondérée
    curiosity = questions_ratio * 0.5 + exploration_ratio * 0.5
    return min(1.0, max(0.0, curiosity))


def calculate_trait_drift(initial_traits: Dict[str, Any], final_traits: Dict[str, Any]) -> float:
    """
    Calcule la dérive des traits entre l'état initial et final.
    
    Utilise la distance cosinus entre les valeurs des traits.
    """
    if not initial_traits or not final_traits:
        return 0.0
    
    # Extraire les valeurs des traits communs
    common_trait_ids = set(initial_traits.keys()) & set(final_traits.keys())
    if not common_trait_ids:
        return 0.0
    
    # Calculer la distance pour chaque trait commun
    drift_scores = []
    for trait_id in common_trait_ids:
        initial_value = initial_traits[trait_id].get("value", "")
        final_value = final_traits[trait_id].get("value", "")
        
        # Si les valeurs sont identiques, drift = 0
        if initial_value == final_value:
            drift_scores.append(0.0)
        else:
            # Calculer une distance simple basée sur la similarité de chaînes
            # (pour une vraie implémentation, on utiliserait des embeddings)
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, str(initial_value), str(final_value)).ratio()
            drift = 1.0 - similarity
            drift_scores.append(drift)
    
    if not drift_scores:
        return 0.0
    
    # Moyenne des drifts
    trait_drift = sum(drift_scores) / len(drift_scores)
    return min(1.0, max(0.0, trait_drift))


def calculate_coherence(
    messages: List[MultiAgentMessage],
    agent_id: str,
    initial_traits: Optional[Dict] = None
) -> float:
    """
    Calcule la cohérence (stabilité de la personnalité).
    
    Formule: mean(governance_scores.coherence) * 0.7 + (1 - trait_drift) * 0.3
    """
    agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
    
    if not agent_messages:
        return 0.0
    
    # 1. Score moyen de cohérence (via gouvernance)
    coherence_scores = []
    for msg in agent_messages:
        if msg.metadata and "scores" in msg.metadata:
            scores = msg.metadata["scores"]
            if isinstance(scores, dict) and "coherence" in scores:
                coherence_scores.append(float(scores["coherence"]))
    
    if not coherence_scores:
        mean_coherence = 0.5  # Valeur par défaut
    else:
        mean_coherence = sum(coherence_scores) / len(coherence_scores)
    
    # 2. Calculer la dérive des traits
    trait_drift = 0.0
    if initial_traits:
        # Pour récupérer les traits finaux, on devrait appeler memory_service
        # Pour l'instant, on assume pas de dérive si initial_traits est fourni
        # mais pas de final_traits
        # TODO: Récupérer les traits finaux depuis memory_service via l'adapter
        # Pour l'instant, on utilise une valeur par défaut
        trait_drift = 0.0  # Pas de dérive par défaut
    
    # 3. Combinaison pondérée
    coherence = mean_coherence * 0.7 + (1 - trait_drift) * 0.3
    return min(1.0, max(0.0, coherence))


def calculate_all_metrics(
    messages: List[MultiAgentMessage],
    agent_id: Optional[str] = None,
    initial_traits: Optional[Dict] = None
) -> BehavioralMetrics:
    """
    Calcule toutes les métriques comportementales.
    
    Si agent_id est None, calcule les métriques globales (variabilité uniquement).
    """
    if agent_id:
        return BehavioralMetrics(
            variability=calculate_variability(messages),
            autonomy=calculate_autonomy(messages, agent_id),
            curiosity=calculate_curiosity(messages, agent_id),
            coherence=calculate_coherence(messages, agent_id, initial_traits)
        )
    else:
        # Métriques globales (variabilité uniquement)
        return BehavioralMetrics(
            variability=calculate_variability(messages),
            autonomy=0.0,
            curiosity=0.0,
            coherence=0.0
        )


def calculate_metrics_by_agent(
    messages: List[MultiAgentMessage],
    agent_ids: List[str],
    initial_traits: Optional[Dict[str, Dict]] = None,
    final_traits: Optional[Dict[str, Dict]] = None
) -> Dict[str, BehavioralMetrics]:
    """Calcule les métriques pour chaque agent."""
    metrics_by_agent = {}
    
    for agent_id in agent_ids:
        initial = initial_traits.get(agent_id) if initial_traits else None
        final = final_traits.get(agent_id) if final_traits else None
        
        # Calculer trait_drift si on a les deux
        trait_drift = 0.0
        if initial and final:
            trait_drift = calculate_trait_drift(initial, final)
        
        # Calculer les métriques
        metrics = calculate_all_metrics(
            messages,
            agent_id=agent_id,
            initial_traits=initial
        )
        
        # Ajuster la cohérence avec trait_drift si disponible
        if initial and final:
            # Recalculer cohérence avec trait_drift réel
            agent_messages = [msg for msg in messages if msg.agent_id == agent_id]
            coherence_scores = []
            for msg in agent_messages:
                if msg.metadata and "scores" in msg.metadata:
                    scores = msg.metadata["scores"]
                    if isinstance(scores, dict) and "coherence" in scores:
                        coherence_scores.append(float(scores["coherence"]))
            
            mean_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.5
            metrics.coherence = mean_coherence * 0.7 + (1 - trait_drift) * 0.3
            metrics.coherence = min(1.0, max(0.0, metrics.coherence))
        
        metrics_by_agent[agent_id] = metrics
    
    return metrics_by_agent
