import random

import numpy as np

from opt import two_opt_cross_check


def calculate_distance(path, distances):
    total = 0
    for i in range(len(path) - 1):
        total += distances[path[i]][path[i + 1]]
    total += distances[path[-1]][path[0]]
    return total


# def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # sabit
#     return 0.5

def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation):  # Lineer azalma / best
    progress = iteration / (n_iterations - 1)
    evaporation = start_evaporation - (start_evaporation - end_evaporation) * progress
    return evaporation


# def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # Ussel azalma
#     progress = np.log1p(iteration) / np.log1p(n_iterations - 1)
#     evaporation = start_evaporation - (start_evaporation - end_evaporation) * progress
#     return evaporation

# def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # Logaritmik azalma
#     ratio = iteration / (n_iterations - 1)
#     evaporation = start_evaporation * ((end_evaporation / start_evaporation) ** ratio)
#     return evaporation


def run_aco(
    distances,
    coords=None,
    n_ants=20,
    n_iterations=100,
    alpha=1,
    beta=3,
    evaporation=0.5,
    q=100,
    end_evaporation=0.1,
    cross_check=True
):
    n_cities = len(distances)
    pheromone = np.ones((n_cities, n_cities), dtype=float)

    global_best_distance = float("inf")
    global_best_path = None
    best_per_iteration = []
    evaporation_history = []

    for iteration in range(n_iterations):
        all_paths = []
        all_distances = []

        current_evaporation = get_evaporation_rate(
            iteration=iteration,
            n_iterations=n_iterations,
            start_evaporation=evaporation,
            end_evaporation=end_evaporation
        )
        evaporation_history.append(current_evaporation)

        for _ in range(n_ants):
            start_city = random.randint(0, n_cities - 1)
            visited = [start_city]
            visited_set = {start_city}

            while len(visited) < n_cities:
                current = visited[-1]
                probabilities = np.zeros(n_cities, dtype=float)

                for city in range(n_cities):
                    if city not in visited_set:
                        tau = pheromone[current][city] ** alpha
                        eta = (1.0 / distances[current][city]) ** beta
                        probabilities[city] = tau * eta

                total_probability = probabilities.sum()

                if total_probability == 0:
                    candidates = [city for city in range(n_cities) if city not in visited_set]
                    next_city = random.choice(candidates)
                else:
                    probabilities /= total_probability
                    next_city = np.random.choice(np.arange(n_cities), p=probabilities)

                visited.append(next_city)
                visited_set.add(next_city)

            if cross_check and coords is not None:
                visited = two_opt_cross_check(visited, coords)

            dist = calculate_distance(visited, distances)
            all_paths.append(visited)
            all_distances.append(dist)

            if dist < global_best_distance:
                global_best_distance = dist
                global_best_path = visited[:]

        best_per_iteration.append(min(all_distances))

        pheromone *= (1 - current_evaporation)

        for path, dist in zip(all_paths, all_distances):
            deposit = q / dist

            for i in range(len(path) - 1):
                a = path[i]
                b = path[i + 1]
                pheromone[a][b] += deposit
                pheromone[b][a] += deposit

            a = path[-1]
            b = path[0]
            pheromone[a][b] += deposit
            pheromone[b][a] += deposit

    return global_best_path, global_best_distance, pheromone, best_per_iteration, evaporation_history
