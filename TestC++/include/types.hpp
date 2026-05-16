#pragma once

#include <limits>
#include <random>
#include <vector>

struct Point {
    double x = 0.0;
    double y = 0.0;
};

using Matrix = std::vector<std::vector<double>>;

struct DistanceData {
    Matrix distances;
    std::vector<Point> coords;
};

struct BlindRoundRecord {
    int aco_iteration = 0;
    int blind_iteration = 0;
    int blind_total_iterations = 0;
    double best_distance = 0.0;
};

struct BlindAcoResult {
    Matrix pheromone;
    std::vector<double> best_per_iteration;
};

struct AcoResult {
    std::vector<int> best_path;
    double best_distance = std::numeric_limits<double>::infinity();
    Matrix pheromone;
    std::vector<double> best_per_iteration;
    std::vector<double> evaporation_history;
    std::vector<BlindRoundRecord> blind_round_history;
};

struct RandomContext {
    std::mt19937 python_rng;
    std::mt19937 numpy_rng;

    RandomContext(unsigned int python_seed, unsigned int numpy_seed)
        : python_rng(python_seed), numpy_rng(numpy_seed) {}
};
