import random

import numpy as np

from blindAco import blend_pheromones, run_blind_aco
from opt import two_opt_cross_check
from pheromone import (
    apply_min_max_pheromone,
    calculate_min_max_pheromone_bounds,
    create_initial_pheromone,
)


def calculate_distance(path, distances):
    total = 0
    for i in range(len(path) - 1):
        total += distances[path[i]][path[i + 1]]
    total += distances[path[-1]][path[0]]
    return total


def vary_parameter(value, variation):
    if variation <= 0:
        return value

    lower_multiplier = max(0.0, 1 - variation)
    upper_multiplier = 1 + variation
    return value * random.uniform(lower_multiplier, upper_multiplier)


def select_pheromone_deposit_paths(all_paths, all_distances, deposit_top_ants):
    if deposit_top_ants is None:
        return zip(all_paths, all_distances)

    deposit_count = max(0, min(int(deposit_top_ants), len(all_paths)))

    if deposit_count == 0:
        return []

    selected_indices = sorted(
        range(len(all_distances)),
        key=lambda index: all_distances[index]
    )[:deposit_count]
    return [
        (all_paths[index], all_distances[index])
        for index in selected_indices
    ]


def _clamp01(value):
    return min(max(value, 0.0), 1.0)


def _exponential_progress(progress, curve):
    if abs(curve) < 1e-12:
        return progress

    numerator = np.exp(curve * progress) - 1.0
    denominator = np.exp(curve) - 1.0

    if abs(denominator) < 1e-12:
        return progress

    return float(_clamp01(numerator / denominator))


def _logarithmic_progress(progress, curve):
    bend = abs(curve)

    if bend < 1e-12:
        return progress

    denominator = np.log1p(bend)

    if denominator <= 0:
        return progress

    if curve >= 0:
        return float(_clamp01(np.log1p(bend * progress) / denominator))

    return float(_clamp01(
        1.0 - np.log1p(bend * (1.0 - progress)) / denominator
    ))


def get_evaporation_rate(
    iteration,
    n_iterations,
    start_evaporation,
    end_evaporation,
    schedule="linear",
    curve=1.0
):
    if n_iterations <= 1:
        return start_evaporation

    progress = iteration / (n_iterations - 1)
    normalized_schedule = schedule.lower()

    if normalized_schedule == "linear":
        shaped_progress = progress
    elif normalized_schedule in ("exponential", "exp", "ussel", "üstel"):
        shaped_progress = _exponential_progress(progress, curve)
    elif normalized_schedule in ("logarithmic", "log", "logaritmik"):
        shaped_progress = _logarithmic_progress(progress, curve)
    else:
        raise ValueError(
            "evaporation_schedule must be linear, exponential, or logarithmic"
        )

    evaporation = start_evaporation - (
        start_evaporation - end_evaporation
    ) * shaped_progress
    return float(evaporation)


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
    ant_parameter_variation=0.1,
    use_min_max_pheromone=False,
    min_max_tau_ratio=2.0,
    pheromone_deposit_top_ants=None,
    evaporation_schedule="linear",
    evaporation_curve=1.0,
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
            end_evaporation=end_evaporation,
            schedule=evaporation_schedule,
            curve=evaporation_curve
        )
        evaporation_history.append(current_evaporation)

        for _ in range(n_ants):
            ant_alpha = vary_parameter(alpha, ant_parameter_variation)
            ant_beta = vary_parameter(beta, ant_parameter_variation)
            start_city = random.randint(0, n_cities - 1)
            visited = [start_city]
            visited_set = {start_city}

            while len(visited) < n_cities:
                current = visited[-1]
                probabilities = np.zeros(n_cities, dtype=float)

                for city in range(n_cities):
                    if city not in visited_set:
                        tau = pheromone[current][city] ** ant_alpha
                        eta = (1.0 / distances[current][city]) ** ant_beta
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

        for path, dist in select_pheromone_deposit_paths(
            all_paths=all_paths,
            all_distances=all_distances,
            deposit_top_ants=pheromone_deposit_top_ants
        ):
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

        if use_min_max_pheromone:
            apply_min_max_pheromone(
                pheromone=pheromone,
                q=q,
                evaporation=current_evaporation,
                best_distance=global_best_distance,
                tau_ratio=min_max_tau_ratio
            )

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
            blind_pheromone_bounds = None

            if use_min_max_pheromone:
                blind_pheromone_bounds = calculate_min_max_pheromone_bounds(
                    q=q,
                    evaporation=current_evaporation,
                    best_distance=global_best_distance,
                    n_cities=n_cities,
                    tau_ratio=min_max_tau_ratio
                )

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
                beta_variation=ant_parameter_variation,
                use_min_max_pheromone=use_min_max_pheromone,
                min_max_tau_ratio=min_max_tau_ratio,
                pheromone_bounds=blind_pheromone_bounds,
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
                blind_weight=blind_blend_weight,
                normalize_blind=blind_pheromone_bounds is None
            )
            if use_min_max_pheromone:
                apply_min_max_pheromone(
                    pheromone=pheromone,
                    q=q,
                    evaporation=current_evaporation,
                    best_distance=global_best_distance,
                    tau_ratio=min_max_tau_ratio
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
