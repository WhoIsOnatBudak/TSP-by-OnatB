#pragma once

#include "types.hpp"

#include <optional>

Matrix createInitialPheromone(
    const Matrix& distances,
    double base_pheromone = 1.0,
    std::optional<double> nearest_neighbor_pheromone = 1.1
);
