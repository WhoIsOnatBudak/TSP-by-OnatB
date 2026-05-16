#include "aco.hpp"

#include "blind_aco.hpp"
#include "opt.hpp"
#include "pheromone.hpp"
#include "tour.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <numeric>
#include <random>

namespace {

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
                            params.alpha
                        );
                        const double eta = std::pow(
                            1.0 / distances[static_cast<std::size_t>(current)]
                                [static_cast<std::size_t>(city)],
                            params.beta
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

        for (std::size_t index = 0; index < all_paths.size(); ++index) {
            depositPheromone(
                pheromone,
                all_paths[index],
                all_distances[index],
                params.q
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
                params.blind_blend_weight
            );
            stagnation_counter = 0;
        }
    }

    result.pheromone = pheromone;
    return result;
}
