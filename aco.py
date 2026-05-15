import random

import numpy as np

from blindAco import blend_pheromones, run_blind_aco
from opt import two_opt_cross_check
from pheromone import create_initial_pheromone


def calculate_distance(path, distances):
    total = 0
    for i in range(len(path) - 1):
        total += distances[path[i]][path[i + 1]]
    total += distances[path[-1]][path[0]]
    return total


# def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # sabit
#     return 0.5

#def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation):  # Lineer azalma / best
#    progress = iteration / (n_iterations - 1)
#    evaporation = start_evaporation - (start_evaporation - end_evaporation) * progress
#    return evaporation


def get_evaporation_rate(iteration, n_iterations, start_evaporation, end_evaporation): # Ussel azalma
     progress = np.log1p(iteration) / np.log1p(n_iterations - 1)
     evaporation = start_evaporation - (start_evaporation - end_evaporation) * progress
     return evaporation

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
    cross_check=True,
    base_pheromone=1.0,
    nearest_neighbor_pheromone=1.1,
    blind_stagnation_limit=10,
    blind_iterations=5,
    blind_blend_weight=0.3,
    return_blind_history=False
):
    n_cities = len(distances)
    pheromone = create_initial_pheromone(
        distances=distances,
        base_pheromone=base_pheromone,
        nearest_neighbor_pheromone=nearest_neighbor_pheromone
    )

    global_best_distance = float("inf")
    global_best_path = None
    best_per_iteration = []
    evaporation_history = []
    blind_round_history = []
    stagnation_counter = 0

    for iteration in range(n_iterations):
        all_paths = []
        all_distances = []
        improved_this_iteration = False

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
                improved_this_iteration = True

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

        if improved_this_iteration:
            stagnation_counter = 0
        else:
            stagnation_counter += 1

        if (
            blind_stagnation_limit is not None
            and stagnation_counter >= blind_stagnation_limit
            and blind_iterations > 0
            and blind_blend_weight > 0
        ):
            blind_pheromone, blind_best_per_iteration = run_blind_aco(
                distances=distances,
                coords=coords,
                n_ants=n_ants,
                n_iterations=blind_iterations,
                beta=beta,
                evaporation=current_evaporation,
                q=q,
                base_pheromone=base_pheromone,
                cross_check=cross_check,
                return_history=True
            )
            for blind_iteration, best_distance in enumerate(blind_best_per_iteration):
                blind_round_history.append({
                    "aco_iteration": iteration,
                    "blind_iteration": blind_iteration,
                    "blind_total_iterations": blind_iterations,
                    "best_distance": best_distance
                })

            pheromone = blend_pheromones(
                current_pheromone=pheromone,
                blind_pheromone=blind_pheromone,
                blind_weight=blind_blend_weight
            )
            stagnation_counter = 0

    result = (
        global_best_path,
        global_best_distance,
        pheromone,
        best_per_iteration,
        evaporation_history
    )

    if return_blind_history:
        return result + (blind_round_history,)

    return result
