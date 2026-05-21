#include "ant_builder.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>

namespace aco {

double varyParameter(
    double value,
    double variation,
    std::mt19937& rng
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

    return value * distribution(rng);
}

namespace {

int chooseByWeights(
    const std::vector<double>& weights,
    double total_weight,
    std::mt19937& rng
) {
    std::uniform_real_distribution<double> distribution(0.0, total_weight);
    const double target = distribution(rng);
    double cumulative = 0.0;

    for (std::size_t city = 0; city < weights.size(); ++city) {
        cumulative += weights[city];

        if (target <= cumulative) {
            return static_cast<int>(city);
        }
    }

    return static_cast<int>(weights.size() - 1);
}

std::vector<int> unvisitedCandidates(const std::vector<bool>& visited) {
    std::vector<int> candidates;

    for (std::size_t city = 0; city < visited.size(); ++city) {
        if (!visited[city]) {
            candidates.push_back(static_cast<int>(city));
        }
    }

    return candidates;
}

}  // namespace

std::vector<int> buildAntPath(
    const Matrix& distances,
    const Matrix& pheromone,
    const Params& params,
    double parameter_variation,
    std::mt19937& rng
) {
    const int n_cities = static_cast<int>(distances.size());
    std::uniform_int_distribution<int> start_distribution(0, n_cities - 1);
    const int start_city = start_distribution(rng);

    const double ant_alpha = varyParameter(
        params.alpha,
        parameter_variation,
        rng
    );
    const double ant_beta = varyParameter(
        params.beta,
        parameter_variation,
        rng
    );

    std::vector<int> path = {start_city};
    std::vector<bool> visited(static_cast<std::size_t>(n_cities), false);
    visited[static_cast<std::size_t>(start_city)] = true;

    while (static_cast<int>(path.size()) < n_cities) {
        const int current = path.back();
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
                probabilities[static_cast<std::size_t>(city)] = tau * eta;
            }
        }

        const double total_probability = std::accumulate(
            probabilities.begin(),
            probabilities.end(),
            0.0
        );

        int next_city = 0;

        if (total_probability == 0.0) {
            const std::vector<int> candidates = unvisitedCandidates(visited);
            std::uniform_int_distribution<int> candidate_distribution(
                0,
                static_cast<int>(candidates.size()) - 1
            );
            next_city = candidates[
                static_cast<std::size_t>(candidate_distribution(rng))
            ];
        } else {
            next_city = chooseByWeights(probabilities, total_probability, rng);
        }

        path.push_back(next_city);
        visited[static_cast<std::size_t>(next_city)] = true;
    }

    return path;
}

std::vector<int> buildDistanceOnlyPath(
    const Matrix& distances,
    const Params& params,
    std::mt19937& rng
) {
    const int n_cities = static_cast<int>(distances.size());
    std::uniform_int_distribution<int> start_distribution(0, n_cities - 1);
    const int start_city = start_distribution(rng);
    const double ant_beta = varyParameter(
        params.beta,
        params.ant_parameter_variation,
        rng
    );

    std::vector<int> path = {start_city};
    std::vector<bool> visited(static_cast<std::size_t>(n_cities), false);
    visited[static_cast<std::size_t>(start_city)] = true;

    while (static_cast<int>(path.size()) < n_cities) {
        const int current = path.back();
        std::vector<double> probabilities(
            static_cast<std::size_t>(n_cities),
            0.0
        );

        for (int city = 0; city < n_cities; ++city) {
            if (!visited[static_cast<std::size_t>(city)]) {
                probabilities[static_cast<std::size_t>(city)] = std::pow(
                    1.0 / distances[static_cast<std::size_t>(current)]
                        [static_cast<std::size_t>(city)],
                    ant_beta
                );
            }
        }

        const double total_probability = std::accumulate(
            probabilities.begin(),
            probabilities.end(),
            0.0
        );

        int next_city = 0;

        if (total_probability == 0.0) {
            const std::vector<int> candidates = unvisitedCandidates(visited);
            std::uniform_int_distribution<int> candidate_distribution(
                0,
                static_cast<int>(candidates.size()) - 1
            );
            next_city = candidates[
                static_cast<std::size_t>(candidate_distribution(rng))
            ];
        } else {
            next_city = chooseByWeights(probabilities, total_probability, rng);
        }

        path.push_back(next_city);
        visited[static_cast<std::size_t>(next_city)] = true;
    }

    return path;
}

}  // namespace aco

