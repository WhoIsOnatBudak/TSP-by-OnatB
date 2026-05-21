#include "aco.hpp"

#include "blind_aco.hpp"
#include "opt.hpp"
#include "pheromone.hpp"
#include "tour.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <numeric>
#include <optional>
#include <random>
#include <utility>

namespace {

double varyParameter(
    double value,
    double variation,
    RandomContext& rng
) {
    if (variation <= 0.0) {
        return value;
    }

    const double lower_multiplier = std::max(0.0, 1.0 - variation);
    const double upper_multiplier = 1.0 + variation;
    std::uniform_real_distribution<double> distribution(
        lower_multiplier,
        upper_multiplier
    );

    return value * distribution(rng.python_rng);
}

int chooseByWeights(
    const std::vector<double>& weights,
    double total_weight,
    RandomContext& rng
) {
    std::uniform_real_distribution<double> distribution(0.0, total_weight);
    const double target = distribution(rng.numpy_rng);
    double cumulative = 0.0;

    for (std::size_t city = 0; city < weights.size(); ++city) {
        cumulative += weights[city];

        if (target <= cumulative) {
            return static_cast<int>(city);
        }
    }

    return static_cast<int>(weights.size() - 1);
}

std::vector<int> chooseCandidate(
    const std::vector<bool>& visited
) {
    std::vector<int> candidates;

    for (std::size_t city = 0; city < visited.size(); ++city) {
        if (!visited[city]) {
            candidates.push_back(static_cast<int>(city));
        }
    }

    return candidates;
}

std::vector<std::size_t> selectPheromoneDepositIndices(
    const std::vector<double>& all_distances,
    std::optional<int> deposit_top_ants
) {
    std::vector<std::size_t> indices(all_distances.size());
    std::iota(indices.begin(), indices.end(), 0);

    if (!deposit_top_ants.has_value()) {
        return indices;
    }

    const std::size_t deposit_count = std::min(
        static_cast<std::size_t>(std::max(*deposit_top_ants, 0)),
        all_distances.size()
    );

    if (deposit_count == 0) {
        return {};
    }

    std::sort(
        indices.begin(),
        indices.end(),
        [&](std::size_t left, std::size_t right) {
            return all_distances[left] < all_distances[right];
        }
    );
    indices.resize(deposit_count);
    return indices;
}

} // namespace

double getEvaporationRate(
    int iteration,
    int n_iterations,
    double start_evaporation,
    double end_evaporation
) {
    if (n_iterations <= 1) {
        return start_evaporation;
    }

    const double progress = static_cast<double>(iteration)
        / static_cast<double>(n_iterations - 1);
    return start_evaporation
        - (start_evaporation - end_evaporation) * progress;
}

AcoResult runAco(
    const Matrix& distances,
    const std::vector<Point>* coords,
    const AcoParams& params,
    RandomContext& rng
) {
    const int n_cities = static_cast<int>(distances.size());
    Matrix pheromone = createInitialPheromone(
        distances,
        params.base_pheromone,
        params.nearest_neighbor_pheromone
    );

    AcoResult result;
    result.pheromone = pheromone;

    int stagnation_counter = 0;

    for (int iteration = 0; iteration < params.n_iterations; ++iteration) {
        std::vector<std::vector<int>> all_paths;
        std::vector<double> all_distances;
        bool improved_this_iteration = false;

        const double current_evaporation = getEvaporationRate(
            iteration,
            params.n_iterations,
            params.evaporation,
            params.end_evaporation
        );
        result.evaporation_history.push_back(current_evaporation);

        for (int ant = 0; ant < params.n_ants; ++ant) {
            const double ant_alpha = varyParameter(
                params.alpha,
                params.ant_parameter_variation,
                rng
            );
            const double ant_beta = varyParameter(
                params.beta,
                params.ant_parameter_variation,
                rng
            );
            std::uniform_int_distribution<int> start_distribution(
                0,
                n_cities - 1
            );
            const int start_city = start_distribution(rng.python_rng);
            std::vector<int> visited_path = {start_city};
            std::vector<bool> visited(
                static_cast<std::size_t>(n_cities),
                false
            );
            visited[static_cast<std::size_t>(start_city)] = true;

            while (static_cast<int>(visited_path.size()) < n_cities) {
                const int current = visited_path.back();
                std::vector<double> probabilities(
                    static_cast<std::size_t>(n_cities),
                    0.0
                );

                for (int city = 0; city < n_cities; ++city) {
                    if (!visited[static_cast<std::size_t>(city)]) {
                        const double tau = std::pow(
                            pheromone[static_cast<std::size_t>(current)]
                                [static_cast<std::size_t>(city)],
                            ant_alpha
                        );
                        const double eta = std::pow(
                            1.0 / distances[static_cast<std::size_t>(current)]
                                [static_cast<std::size_t>(city)],
                            ant_beta
                        );
                        probabilities[static_cast<std::size_t>(city)] =
                            tau * eta;
                    }
                }

                const double total_probability = std::accumulate(
                    probabilities.begin(),
                    probabilities.end(),
                    0.0
                );

                int next_city = 0;

                if (total_probability == 0.0) {
                    const std::vector<int> candidates =
                        chooseCandidate(visited);
                    std::uniform_int_distribution<int> candidate_distribution(
                        0,
                        static_cast<int>(candidates.size()) - 1
                    );
                    next_city = candidates[
                        static_cast<std::size_t>(
                            candidate_distribution(rng.python_rng)
                        )
                    ];
                } else {
                    next_city = chooseByWeights(
                        probabilities,
                        total_probability,
                        rng
                    );
                }

                visited_path.push_back(next_city);
                visited[static_cast<std::size_t>(next_city)] = true;
            }

            if (params.cross_check && coords != nullptr) {
                visited_path = twoOptCrossCheck(visited_path, *coords);
            }

            const double distance = calculateDistance(visited_path, distances);
            all_paths.push_back(visited_path);
            all_distances.push_back(distance);

            if (distance < result.best_distance) {
                result.best_distance = distance;
                result.best_path = visited_path;
                improved_this_iteration = true;
            }
        }

        result.best_per_iteration.push_back(
            *std::min_element(all_distances.begin(), all_distances.end())
        );

        for (std::vector<double>& row : pheromone) {
            for (double& value : row) {
                value *= (1.0 - current_evaporation);
            }
        }

        const std::vector<std::size_t> deposit_indices =
            selectPheromoneDepositIndices(
                all_distances,
                params.pheromone_deposit_top_ants
            );

        for (std::size_t index : deposit_indices) {
            depositPheromone(
                pheromone,
                all_paths[index],
                all_distances[index],
                params.q
            );
        }

        if (params.use_min_max_pheromone) {
            applyMinMaxPheromone(
                pheromone,
                params.q,
                current_evaporation,
                result.best_distance,
                n_cities,
                params.min_max_tau_ratio
            );
        }

        if (improved_this_iteration) {
            stagnation_counter = 0;
        } else {
            ++stagnation_counter;
        }

        if (
            params.blind_stagnation_limit.has_value()
            && stagnation_counter >= *params.blind_stagnation_limit
            && params.blind_iterations > 0
            && params.blind_blend_weight > 0.0
        ) {
            std::optional<std::pair<double, double>> blind_pheromone_bounds;

            if (params.use_min_max_pheromone) {
                double tau_min = 0.0;
                double tau_max = 0.0;

                if (calculateMinMaxPheromoneBounds(
                    params.q,
                    current_evaporation,
                    result.best_distance,
                    n_cities,
                    params.min_max_tau_ratio,
                    tau_min,
                    tau_max
                )) {
                    blind_pheromone_bounds = std::make_pair(tau_min, tau_max);
                }
            }

            BlindAcoResult blind_result = runBlindAco(
                distances,
                coords,
                params.n_ants,
                params.blind_iterations,
                params.beta,
                current_evaporation,
                params.q,
                params.base_pheromone,
                params.cross_check,
                params.ant_parameter_variation,
                params.use_min_max_pheromone,
                params.min_max_tau_ratio,
                blind_pheromone_bounds,
                rng
            );

            for (
                std::size_t blind_iteration = 0;
                blind_iteration < blind_result.best_per_iteration.size();
                ++blind_iteration
            ) {
                result.blind_round_history.push_back({
                    iteration,
                    static_cast<int>(blind_iteration),
                    params.blind_iterations,
                    blind_result.best_per_iteration[blind_iteration]
                });
            }

            pheromone = blendPheromones(
                pheromone,
                blind_result.pheromone,
                params.blind_blend_weight,
                !blind_pheromone_bounds.has_value()
            );

            if (params.use_min_max_pheromone) {
                applyMinMaxPheromone(
                    pheromone,
                    params.q,
                    current_evaporation,
                    result.best_distance,
                    n_cities,
                    params.min_max_tau_ratio
                );
            }

            stagnation_counter = 0;
        }
    }

    result.pheromone = pheromone;
    return result;
}
