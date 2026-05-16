#include "generation.hpp"

#include <cmath>
#include <random>

DistanceData generateEuclideanDistances(
    int n_cities,
    unsigned int seed,
    double scale,
    RandomContext* rng
) {
    std::mt19937 local_rng(seed);
    std::mt19937& coord_rng = rng ? rng->numpy_rng : local_rng;

    if (rng) {
        rng->numpy_rng.seed(seed);
    }

    std::uniform_real_distribution<double> unit_distribution(0.0, 1.0);
    std::vector<Point> coords(static_cast<std::size_t>(n_cities));

    for (Point& point : coords) {
        point.x = unit_distribution(coord_rng) * scale;
        point.y = unit_distribution(coord_rng) * scale;
    }

    Matrix distances(
        static_cast<std::size_t>(n_cities),
        std::vector<double>(static_cast<std::size_t>(n_cities), 0.0)
    );

    for (int i = 0; i < n_cities; ++i) {
        for (int j = 0; j < n_cities; ++j) {
            const double dx = coords[static_cast<std::size_t>(i)].x
                - coords[static_cast<std::size_t>(j)].x;
            const double dy = coords[static_cast<std::size_t>(i)].y
                - coords[static_cast<std::size_t>(j)].y;
            distances[static_cast<std::size_t>(i)][static_cast<std::size_t>(j)] =
                std::sqrt(dx * dx + dy * dy);
        }
    }

    return {distances, coords};
}
