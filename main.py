import random

import numpy as np

from aco import run_aco
from plots import (
    plot_best_tour,
    plot_cities,
    plot_convergence,
    plot_evaporation,
    plot_pheromone_heatmap,
)


def generate_euclidean_distances(n_cities, seed=42, scale=100):
    np.random.seed(seed)
    coords = np.random.rand(n_cities, 2) * scale
    distances = np.zeros((n_cities, n_cities), dtype=float)

    for i in range(n_cities):
        for j in range(n_cities):
            distances[i][j] = np.linalg.norm(coords[i] - coords[j])

    return distances, coords


def main():
    random.seed(43)
    np.random.seed(43)

    n_cities = 30
    distances, coords = generate_euclidean_distances(
        n_cities=n_cities,
        seed=47,
        scale=n_cities * 20
    )

    (
        best_path,
        best_distance,
        pheromone,
        best_per_iteration,
        evaporation_history,
        blind_round_history
    ) = run_aco(
        distances=distances,
        coords=coords,
        n_ants=40,
        n_iterations=50,
        alpha=1,
        beta=3,
        evaporation=0.8,
        q=n_cities * 20,
        end_evaporation=0.3,
        base_pheromone=1.0,
        nearest_neighbor_pheromone=1.1,
        blind_stagnation_limit=10,
        blind_iterations=5,
        blind_blend_weight=0.5,
        ant_parameter_variation=0.1,
        use_min_max_pheromone=True,
        min_max_tau_ratio=2.0,
        pheromone_deposit_top_ants=1,
        return_blind_history=True
    )

    print("Best Path:", best_path)
    print("Best Distance:", best_distance)

    plot_cities(coords)
    plot_best_tour(coords, best_path)
    plot_pheromone_heatmap(pheromone)
    plot_convergence(best_per_iteration, blind_round_history)
    plot_evaporation(evaporation_history)


if __name__ == "__main__":
    main()
