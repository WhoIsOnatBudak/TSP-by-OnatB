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
