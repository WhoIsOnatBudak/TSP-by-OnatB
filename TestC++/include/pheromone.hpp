#pragma once

#include "types.hpp"

#include <cstddef>
#include <optional>

Matrix createFlatPheromone(
    std::size_t n_cities,
    double base_pheromone
);

Matrix createInitialPheromone(
    const Matrix& distances,
    double base_pheromone = 1.0,
    std::optional<double> nearest_neighbor_pheromone = 1.1
);

bool calculateMinMaxPheromoneBounds(
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double tau_ratio,
    double& tau_min,
    double& tau_max
);

void applyMinMaxPheromone(
    Matrix& pheromone,
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double tau_ratio
);
