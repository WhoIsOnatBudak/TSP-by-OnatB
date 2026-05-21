import numpy as np


def create_initial_pheromone(
    distances,
    base_pheromone=1.0,
    nearest_neighbor_pheromone=1.1
):
    n_cities = len(distances)
    pheromone = np.full((n_cities, n_cities), base_pheromone, dtype=float)

    if n_cities < 2:
        return pheromone

    if nearest_neighbor_pheromone is None:
        return pheromone

    masked_distances = np.array(distances, dtype=float, copy=True)
    np.fill_diagonal(masked_distances, np.inf)

    for city in range(n_cities):
        nearest_city = int(np.argmin(masked_distances[city]))
        pheromone[city][nearest_city] = nearest_neighbor_pheromone
        pheromone[nearest_city][city] = nearest_neighbor_pheromone

    return pheromone


def calculate_min_max_pheromone_bounds(
    q,
    evaporation,
    best_distance,
    n_cities,
    tau_ratio=2.0,
    eps=1e-12
):
    if n_cities <= 0 or best_distance <= 0 or not np.isfinite(best_distance):
        return None

    tau_max = q / max(evaporation * best_distance, eps)
    tau_min = tau_max / max(tau_ratio * n_cities, 1.0)
    return tau_min, tau_max


def apply_min_max_pheromone(
    pheromone,
    q,
    evaporation,
    best_distance,
    tau_ratio=2.0
):
    bounds = calculate_min_max_pheromone_bounds(
        q=q,
        evaporation=evaporation,
        best_distance=best_distance,
        n_cities=len(pheromone),
        tau_ratio=tau_ratio
    )

    if bounds is None:
        return pheromone

    tau_min, tau_max = bounds
    np.clip(pheromone, tau_min, tau_max, out=pheromone)
    return pheromone
