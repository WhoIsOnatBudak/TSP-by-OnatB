#pragma once

#include "types.hpp"

#include <vector>

BlindAcoResult runBlindAco(
    const Matrix& distances,
    const std::vector<Point>* coords,
    int n_ants,
    int n_iterations,
    double beta,
    double evaporation,
    double q,
    double base_pheromone,
    bool cross_check,
    RandomContext& rng
);

Matrix blendPheromones(
    const Matrix& current_pheromone,
    Matrix blind_pheromone,
    double blind_weight = 0.3
);
