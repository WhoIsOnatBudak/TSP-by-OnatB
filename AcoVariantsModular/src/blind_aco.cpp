#include "blind_aco.hpp"

#include "ant_builder.hpp"
#include "geometry.hpp"
#include "pheromone.hpp"

#include <algorithm>
#include <limits>

namespace aco {

Matrix runBlindAco(
    const Matrix& distances,
    const std::vector<Point>& coords,
    const Params& params,
    double evaporation,
    std::mt19937& rng,
    bool has_pheromone_bounds,
    double bound_tau_min,
    double bound_tau_max
) {
    Matrix edge_usage_counts = createFlatPheromone(
        distances.size(),
        0.0
    );
    double best_distance_so_far = std::numeric_limits<double>::infinity();

    for (int iteration = 0; iteration < params.blind_iterations; ++iteration) {
        std::vector<double> all_distances;

        for (int ant = 0; ant < params.n_ants; ++ant) {
            std::vector<int> path = buildDistanceOnlyPath(
                distances,
                params,
                rng
            );

            if (params.cross_check) {
                path = twoOptCrossCheck(path, coords);
            }

            all_distances.push_back(calculateDistance(path, distances));
            countPathEdges(edge_usage_counts, path);
        }

        best_distance_so_far = std::min(
            best_distance_so_far,
            *std::min_element(all_distances.begin(), all_distances.end())
        );
    }

    double tau_min = bound_tau_min;
    double tau_max = bound_tau_max;

    if (!has_pheromone_bounds) {
        has_pheromone_bounds = calculateMinMaxBounds(
            params.q,
            evaporation,
            best_distance_so_far,
            params.n_cities,
            params.min_max_tau_ratio,
            tau_min,
            tau_max
        );
    }

    if (!has_pheromone_bounds) {
        tau_min = params.base_pheromone;
        tau_max = params.base_pheromone;
    }

    return createUsageBasedPheromone(edge_usage_counts, tau_min, tau_max);
}

}  // namespace aco

