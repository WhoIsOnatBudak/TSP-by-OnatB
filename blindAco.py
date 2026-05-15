import random

import numpy as np

from opt import two_opt_cross_check
from pheromone import create_initial_pheromone


def _calculate_distance(path, distances):
    total = 0
    for i in range(len(path) - 1):
        total += distances[path[i]][path[i + 1]]
    total += distances[path[-1]][path[0]]
    return total


def _deposit_pheromone(pheromone, path, distance, q):
    deposit = q / distance

    for i in range(len(path) - 1):
        a = path[i]
        b = path[i + 1]
        pheromone[a][b] += deposit
        pheromone[b][a] += deposit

    a = path[-1]
    b = path[0]
    pheromone[a][b] += deposit
    pheromone[b][a] += deposit


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


def run_blind_aco(
    distances,
    coords=None,
    n_ants=20,
    n_iterations=5,
    beta=3,
    evaporation=0.5,
    q=100,
    base_pheromone=1.0,
    cross_check=True
):
    pheromone = create_initial_pheromone(
        distances=distances,
        base_pheromone=base_pheromone,
        nearest_neighbor_pheromone=None
    )

    for _ in range(n_iterations):
        all_paths = []
        all_distances = []

        for _ in range(n_ants):
            path = _build_distance_only_path(distances, beta)

            if cross_check and coords is not None:
                path = two_opt_cross_check(path, coords)

            distance = _calculate_distance(path, distances)
            all_paths.append(path)
            all_distances.append(distance)

        pheromone *= (1 - evaporation)

        for path, distance in zip(all_paths, all_distances):
            _deposit_pheromone(pheromone, path, distance, q)

    return pheromone


def _off_diagonal_mean(matrix):
    n_rows = len(matrix)

    if n_rows < 2:
        return float(np.mean(matrix))

    mask = ~np.eye(n_rows, dtype=bool)
    return float(np.mean(matrix[mask]))


def blend_pheromones(current_pheromone, blind_pheromone, blind_weight=0.3):
    current_weight = 1 - blind_weight
    current_mean = _off_diagonal_mean(current_pheromone)
    blind_mean = _off_diagonal_mean(blind_pheromone)

    if blind_mean > 0:
        blind_pheromone = blind_pheromone * (current_mean / blind_mean)

    return current_weight * current_pheromone + blind_weight * blind_pheromone
