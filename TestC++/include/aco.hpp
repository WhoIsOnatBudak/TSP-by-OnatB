#pragma once

#include "types.hpp"

#include <optional>
#include <vector>

struct AcoParams {
    int n_ants = 20;
    int n_iterations = 100;
    double alpha = 1.0;
    double beta = 3.0;
    double evaporation = 0.5;
    double q = 100.0;
    double end_evaporation = 0.1;
    bool cross_check = true;
    double base_pheromone = 1.0;
    double nearest_neighbor_pheromone = 1.1;
    std::optional<int> blind_stagnation_limit = 10;
    int blind_iterations = 5;
    double blind_blend_weight = 0.3;
    double ant_parameter_variation = 0.1;
    bool use_min_max_pheromone = false;
    double min_max_tau_ratio = 2.0;
    std::optional<int> pheromone_deposit_top_ants = std::nullopt;
};

double getEvaporationRate(
    int iteration,
    int n_iterations,
    double start_evaporation,
    double end_evaporation
);

AcoResult runAco(
    const Matrix& distances,
    const std::vector<Point>* coords,
    const AcoParams& params,
    RandomContext& rng
);
