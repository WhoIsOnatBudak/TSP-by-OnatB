#include "pheromone.hpp"

#include <algorithm>
#include <cstddef>
#include <cmath>
#include <limits>

Matrix createFlatPheromone(
    std::size_t n_cities,
    double base_pheromone
) {
    return Matrix(n_cities, std::vector<double>(n_cities, base_pheromone));
}

Matrix createInitialPheromone(
    const Matrix& distances,
    double base_pheromone,
    std::optional<double> nearest_neighbor_pheromone
) {
    const std::size_t n_cities = distances.size();
    Matrix pheromone = createFlatPheromone(n_cities, base_pheromone);

    if (n_cities < 2 || !nearest_neighbor_pheromone.has_value()) {
        return pheromone;
    }

    for (std::size_t city = 0; city < n_cities; ++city) {
        double best_distance = std::numeric_limits<double>::infinity();
        std::size_t nearest_city = city;

        for (std::size_t candidate = 0; candidate < n_cities; ++candidate) {
            if (candidate == city) {
                continue;
            }

            if (distances[city][candidate] < best_distance) {
                best_distance = distances[city][candidate];
                nearest_city = candidate;
            }
        }

        pheromone[city][nearest_city] = *nearest_neighbor_pheromone;
        pheromone[nearest_city][city] = *nearest_neighbor_pheromone;
    }

    return pheromone;
}

bool calculateMinMaxPheromoneBounds(
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double tau_ratio,
    double& tau_min,
    double& tau_max
) {
    if (
        n_cities <= 0
        || best_distance <= 0.0
        || !std::isfinite(best_distance)
    ) {
        return false;
    }

    tau_max = q / std::max(evaporation * best_distance, 1e-12);
    tau_min = tau_max / std::max(
        tau_ratio * static_cast<double>(n_cities),
        1.0
    );
    return true;
}

void applyMinMaxPheromone(
    Matrix& pheromone,
    double q,
    double evaporation,
    double best_distance,
    int n_cities,
    double tau_ratio
) {
    double tau_min = 0.0;
    double tau_max = 0.0;

    if (!calculateMinMaxPheromoneBounds(
        q,
        evaporation,
        best_distance,
        n_cities,
        tau_ratio,
        tau_min,
        tau_max
    )) {
        return;
    }

    for (std::vector<double>& row : pheromone) {
        for (double& value : row) {
            value = std::clamp(value, tau_min, tau_max);
        }
    }
}
