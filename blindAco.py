import random

import numpy as np

from opt import two_opt_cross_check
from pheromone import calculate_min_max_pheromone_bounds


def _calculate_distance(path, distances):
    total = 0
    for i in range(len(path) - 1):
        total += distances[path[i]][path[i + 1]]
    total += distances[path[-1]][path[0]]
    return total


def _vary_parameter(value, variation):
    if variation <= 0:
        return value

    lower_multiplier = max(0.0, 1 - variation)
    upper_multiplier = 1 + variation
    return value * random.uniform(lower_multiplier, upper_multiplier)


def _build_distance_only_path(distances, beta):
    n_cities = len(distances)
    start_city = random.randint(0, n_cities - 1)
    visited = [start_city]
    visited_set = {start_city}

    while len(visited) < n_cities:
        current = visited[-1]
        probabilities = np.zeros(n_cities, dtype=float)

        for city in range(n_cities):
            if city not in visited_set:
                probabilities[city] = (1.0 / distances[current][city]) ** beta

        total_probability = probabilities.sum()

        if total_probability == 0:
            candidates = [city for city in range(n_cities) if city not in visited_set]
            next_city = random.choice(candidates)
        else:
            probabilities /= total_probability
            next_city = np.random.choice(np.arange(n_cities), p=probabilities)

        visited.append(next_city)
        visited_set.add(next_city)

    return visited


def _count_path_edges(edge_usage_counts, path):
    for i in range(len(path) - 1):
        a = path[i]
        b = path[i + 1]
        edge_usage_counts[a][b] += 1
        edge_usage_counts[b][a] += 1

    a = path[-1]
    b = path[0]
    edge_usage_counts[a][b] += 1
    edge_usage_counts[b][a] += 1


def _create_usage_based_pheromone(edge_usage_counts, pheromone_bounds):
    tau_min, tau_max = pheromone_bounds
    pheromone = np.full(edge_usage_counts.shape, tau_min, dtype=float)
    n_cities = len(edge_usage_counts)

    if n_cities < 2:
        return pheromone

    off_diagonal_mask = ~np.eye(n_cities, dtype=bool)
    off_diagonal_counts = edge_usage_counts[off_diagonal_mask]
    min_count = float(np.min(off_diagonal_counts))
    max_count = float(np.max(off_diagonal_counts))

    if max_count == min_count:
        pheromone[off_diagonal_mask] = (tau_min + tau_max) / 2
        return pheromone

    normalized_counts = (
        edge_usage_counts[off_diagonal_mask] - min_count
    ) / (max_count - min_count)
    pheromone[off_diagonal_mask] = (
        tau_min + normalized_counts * (tau_max - tau_min)
    )
    return pheromone


def run_blind_aco(
    distances,
    coords=None,
    n_ants=20,
    n_iterations=5,
    beta=3,
    evaporation=0.5,
    q=100,
    base_pheromone=1.0,
    cross_check=True,
    beta_variation=0.1,
    use_min_max_pheromone=False,
    min_max_tau_ratio=2.0,
    pheromone_bounds=None,
    return_history=False
):
    n_cities = len(distances)
    edge_usage_counts = np.zeros((n_cities, n_cities), dtype=float)
    best_per_iteration = []
    best_distance_so_far = float("inf")

    for _ in range(n_iterations):
        all_paths = []
        all_distances = []

        for _ in range(n_ants):
            ant_beta = _vary_parameter(beta, beta_variation)
            path = _build_distance_only_path(distances, ant_beta)

            if cross_check and coords is not None:
                path = two_opt_cross_check(path, coords)

            distance = _calculate_distance(path, distances)
            all_paths.append(path)
            all_distances.append(distance)
            _count_path_edges(edge_usage_counts, path)

        iteration_best_distance = min(all_distances)
        best_per_iteration.append(iteration_best_distance)
        best_distance_so_far = min(best_distance_so_far, iteration_best_distance)

    if pheromone_bounds is None:
        pheromone_bounds = calculate_min_max_pheromone_bounds(
            q=q,
            evaporation=evaporation,
            best_distance=best_distance_so_far,
            n_cities=n_cities,
            tau_ratio=min_max_tau_ratio
        )

    if pheromone_bounds is None:
        pheromone_bounds = (base_pheromone, base_pheromone)

    pheromone = _create_usage_based_pheromone(
        edge_usage_counts=edge_usage_counts,
        pheromone_bounds=pheromone_bounds
    )

    if return_history:
        return pheromone, best_per_iteration

    return pheromone


def _off_diagonal_mean(matrix):
    n_rows = len(matrix)

    if n_rows < 2:
        return float(np.mean(matrix))

    mask = ~np.eye(n_rows, dtype=bool)
    return float(np.mean(matrix[mask]))


def blend_pheromones(
    current_pheromone,
    blind_pheromone,
    blind_weight=0.3,
    normalize_blind=True
):
    current_weight = 1 - blind_weight
    current_mean = _off_diagonal_mean(current_pheromone)
    blind_mean = _off_diagonal_mean(blind_pheromone)

    if normalize_blind and blind_mean > 0:
        blind_pheromone = blind_pheromone * (current_mean / blind_mean)

    return current_weight * current_pheromone + blind_weight * blind_pheromone
