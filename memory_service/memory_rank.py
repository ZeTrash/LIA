"""Algorithme MemoryRank : transposition de PageRank pour la mémoire d'un agent.

MemoryRank calcule l'importance structurelle des souvenirs dans un graphe de mémoire,
en se basant sur le principe que "un souvenir est important si d'autres souvenirs 
importants le référencent".
"""

import logging
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class MemoryRank:
    """Implémentation de l'algorithme MemoryRank (PageRank pour la mémoire)."""
    
    def __init__(self, damping_factor: float = 0.85, max_iterations: int = 100, tolerance: float = 1e-6):
        """
        Initialise l'algorithme MemoryRank.
        
        Args:
            damping_factor: Facteur d'amortissement d (≈ 0.85 en pratique)
            max_iterations: Nombre maximum d'itérations pour la convergence
            tolerance: Tolérance pour la convergence
        """
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations
        self.tolerance = tolerance
    
    def compute_ranks(
        self,
        memory_ids: List[str],
        links: List[Tuple[str, str, float]]
    ) -> Dict[str, float]:
        """
        Calcule les scores MemoryRank pour chaque souvenir.
        
        Formule MemoryRank (analogue à PageRank):
        R_j = (1 - d) + d * Σ_i (w_ij / Σ_k w_ik) * R_i
        
        où:
        - R_j = importance du souvenir j
        - d = facteur d'amortissement
        - w_ij = poids du lien du souvenir i vers j
        - Σ_k w_ik = somme des poids des liens sortants de i
        
        Args:
            memory_ids: Liste des IDs de souvenirs
            links: Liste de tuples (source_id, target_id, weight) représentant les liens
        
        Returns:
            Dictionnaire {memory_id: rank_score}
        """
        n = len(memory_ids)
        if n == 0:
            return {}
        
        # Créer un mapping ID -> index
        id_to_index = {mem_id: i for i, mem_id in enumerate(memory_ids)}
        
        # Initialiser la matrice de transition M (n x n)
        # M[i][j] = w_ij / Σ_k w_ik (poids normalisé)
        M = np.zeros((n, n))
        
        # Construire la matrice à partir des liens
        for source_id, target_id, weight in links:
            if source_id in id_to_index and target_id in id_to_index:
                i = id_to_index[source_id]
                j = id_to_index[target_id]
                M[j][i] += weight  # Note: M[j][i] car on veut la transposée pour PageRank
        
        # Normaliser les colonnes (somme des poids sortants par souvenir source)
        # Pour chaque colonne i, diviser par la somme totale des poids sortants
        column_sums = M.sum(axis=0)
        # Éviter division par zéro : si une colonne a somme 0, remplacer par 1/n (téléportation)
        column_sums[column_sums == 0] = 1.0
        M = M / column_sums
        
        # Initialiser le vecteur de rangs (distribution uniforme)
        ranks = np.ones(n) / n
        
        # Itération de PageRank
        for iteration in range(self.max_iterations):
            # Nouveau vecteur de rangs
            # R = (1-d) * (1/n) + d * M * R
            new_ranks = (1 - self.damping_factor) / n + self.damping_factor * M @ ranks
            
            # Vérifier la convergence
            diff = np.abs(new_ranks - ranks).max()
            if diff < self.tolerance:
                logger.debug(f"MemoryRank convergé en {iteration + 1} itérations (diff={diff:.2e})")
                break
            
            ranks = new_ranks
        
        if iteration == self.max_iterations - 1:
            logger.warning(f"MemoryRank n'a pas convergé après {self.max_iterations} itérations")
        
        # Retourner les scores sous forme de dictionnaire
        return {memory_id: float(ranks[id_to_index[memory_id]]) for memory_id in memory_ids}
    
    def compute_ranks_with_temporal_decay(
        self,
        memory_ids: List[str],
        links: List[Tuple[str, str, float]],
        memory_ages: Dict[str, float],
        decay_factor: float = 0.01
    ) -> Dict[str, float]:
        """
        Calcule les scores MemoryRank avec décroissance temporelle.
        
        Extension MemoryRank temporel:
        R_j(t) = R_j * e^(-λ * t)
        
        où:
        - λ = facteur de décroissance
        - t = âge du souvenir (en unités de temps appropriées)
        
        Args:
            memory_ids: Liste des IDs de souvenirs
            links: Liste de tuples (source_id, target_id, weight)
            memory_ages: Dictionnaire {memory_id: age} où age est en jours ou unités temporelles
            decay_factor: Facteur de décroissance λ
        
        Returns:
            Dictionnaire {memory_id: rank_score} avec décroissance temporelle
        """
        # Calculer les rangs de base
        base_ranks = self.compute_ranks(memory_ids, links)
        
        # Appliquer la décroissance temporelle
        decayed_ranks = {}
        for memory_id, base_rank in base_ranks.items():
            age = memory_ages.get(memory_id, 0.0)
            decay = np.exp(-decay_factor * age)
            decayed_ranks[memory_id] = base_rank * decay
        
        return decayed_ranks
    
    def compute_hybrid_score(
        self,
        memory_rank: float,
        reward_score: Optional[float] = None,
        similarity_score: Optional[float] = None,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2
    ) -> float:
        """
        Calcule un score hybride combinant MemoryRank, récompense RL et similarité.
        
        Score = α * Rank + β * Reward + γ * Similarité
        
        Args:
            memory_rank: Score MemoryRank
            reward_score: Score de récompense RL (optionnel)
            similarity_score: Score de similarité (optionnel)
            alpha: Poids pour MemoryRank
            beta: Poids pour Reward
            gamma: Poids pour Similarité
        
        Returns:
            Score hybride normalisé
        """
        score = alpha * memory_rank
        
        if reward_score is not None:
            score += beta * reward_score
        
        if similarity_score is not None:
            score += gamma * similarity_score
        
        # Normaliser si nécessaire (les poids doivent sommer à 1.0)
        total_weight = alpha
        if reward_score is not None:
            total_weight += beta
        if similarity_score is not None:
            total_weight += gamma
        
        if total_weight > 0:
            score = score / total_weight
        
        return score

