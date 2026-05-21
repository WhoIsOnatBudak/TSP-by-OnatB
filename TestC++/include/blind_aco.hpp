#pragma once

#include "types.hpp"

#include <optional>
#include <utility>
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
    double beta_variation,
    bool use_min_max_pheromone,
    double min_max_tau_ratio,
    std::optional<std::pair<double, double>> pheromone_bounds,
    RandomContext& rng
);

Matrix blendPheromones(
    const Matrix& current_pheromone,
    Matrix blind_pheromone,
    double blind_weight = 0.3,
    bool normalize_blind = true
);
