#include "tour.hpp"

#include <cstddef>

double calculateDistance(
    const std::vector<int>& path,
    const Matrix& distances
) {
    double total = 0.0;

    for (std::size_t i = 0; i + 1 < path.size(); ++i) {
        total += distances[static_cast<std::size_t>(path[i])]
            [static_cast<std::size_t>(path[i + 1])];
    }

    total += distances[static_cast<std::size_t>(path.back())]
        [static_cast<std::size_t>(path.front())];

    return total;
}

void depositPheromone(
    Matrix& pheromone,
    const std::vector<int>& path,
    double distance,
    double q
) {
    const double deposit = q / distance;

    for (std::size_t i = 0; i + 1 < path.size(); ++i) {
        const std::size_t a = static_cast<std::size_t>(path[i]);
        const std::size_t b = static_cast<std::size_t>(path[i + 1]);
        pheromone[a][b] += deposit;
        pheromone[b][a] += deposit;
    }

    const std::size_t a = static_cast<std::size_t>(path.back());
    const std::size_t b = static_cast<std::size_t>(path.front());
    pheromone[a][b] += deposit;
    pheromone[b][a] += deposit;
}
