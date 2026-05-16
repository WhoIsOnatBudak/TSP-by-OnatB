#include "pheromone.hpp"

#include <cstddef>
#include <limits>

Matrix createInitialPheromone(
    const Matrix& distances,
    double base_pheromone,
    std::optional<double> nearest_neighbor_pheromone
) {
    const std::size_t n_cities = distances.size();
    Matrix pheromone(n_cities, std::vector<double>(n_cities, base_pheromone));

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
